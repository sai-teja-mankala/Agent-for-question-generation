import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from langgraph.graph import END, StateGraph

from .llm import build_client, get_deployment_name
from .prompts import (
    BLOOM_ALIGNMENT_GENERATION_GUIDANCE,
    DEFAULT_QUALITY_RUBRIC,
    INTERMEDIATE_FORMAT_MCQ,
    OPTIONS_CORRECTION_PROMPT,
    OPTIONS_GENERATION_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RES_FORMAT,
    RES_FORMAT_MULTI_SELECT,
    SCENARIO_GENERATION_PROMPT,
    SYSTEM_CONTRACT,
    SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    SYSTEM_PROMPT_TEMPLATE_QUALITY_CHECK,
    SYSTEM_PROMPT_TEMPLATE_RELEVANCY_CHECK,
    SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT,
    SYSTEM_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_FIX_FORMAT,
    USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    USER_PROMPT_TEMPLATE_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_QUALITY_CHECK,
    USER_PROMPT_TEMPLATE_RELEVANCY_CHECK,
    SYSTEM_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY,
    SYSTEM_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS,
    SYSTEM_PROMPT_TEMPLATE_REVIEWER_TESTTAKER,
    USER_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY,
    USER_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS,
    USER_PROMPT_TEMPLATE_REVIEWER_TESTTAKER,
)
from .qg_types import GraphState, PipelineInput, PromptPayload, QuestionType

logger = logging.getLogger("pipeline")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _extract_json_text(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()
    return stripped


def _parse_json(content: str) -> Any:
    cleaned = _extract_json_text(content)
    parsed = json.loads(cleaned)
    if (
        isinstance(parsed, list)
        and len(parsed) == 1
        and isinstance(parsed[0], dict)
        and "questions" in parsed[0]
    ):
        return parsed[0]
    return parsed


def _parse_json_raw(content: str) -> Any:
    cleaned = _extract_json_text(content)
    return json.loads(cleaned)


def _normalize_learning_objectives(payload: PipelineInput) -> List[Dict[str, Any]]:
    raw = payload.get("learningObjectives") or []
    normalized: List[Dict[str, Any]] = []
    uuid_list = payload.get("learningObjectiveUuid")
    uuid_values: List[str | None] = []
    if isinstance(uuid_list, list):
        uuid_values = [str(val) if val else None for val in uuid_list]
    elif isinstance(uuid_list, str):
        uuid_values = [uuid_list]

    for idx, item in enumerate(raw):
        if isinstance(item, dict):
            description = (
                item.get("description")
                or item.get("learningObjective")
                or item.get("text")
                or ""
            )
            lo_id = item.get("id") or item.get("learningObjectiveUuid")
        else:
            description = str(item)
            lo_id = None
        if not lo_id and idx < len(uuid_values):
            lo_id = uuid_values[idx]
        normalized.append({"id": lo_id, "description": description})
    return normalized


def _learning_objective_descriptions(payload: PipelineInput) -> List[str]:
    return [entry["description"] for entry in _normalize_learning_objectives(payload) if entry.get("description")]


def build_prompt_payloads(state: GraphState) -> GraphState:
    data = state["input"]
    logger.info("Building prompt payloads")
    locale = data.get("locale", "en")
    source_text = data.get("sourceText", "")
    number_of_questions = data.get("numberOfQuestions", 3)
    
    # NEW: Support generating multiple sets per configuration
    # questionsPerSet: how many questions to generate in each payload (default: 1)
    # If numberOfQuestions=9 and questionsPerSet=3, creates 3 payloads of 3 questions each
    # DEFAULT: questionsPerSet=1 generates separate payloads for each question (more diversity)
    questions_per_set = data.get("questionsPerSet", 1)
    
    # Calculate how many payloads needed per configuration
    sets_per_config = max(1, (number_of_questions + questions_per_set - 1) // questions_per_set)
    
    rubric = data.get("qualityRubric") or DEFAULT_QUALITY_RUBRIC.strip()
    bloom_alignment = BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()
    question_types = data.get("questionTypes", ["MULTIPLE_CHOICE"])
    num_correct = data.get("numCorrectOptions", 1)
    num_incorrect = data.get("numIncorrectOptions", 3)
    difficulties: List[str] = data.get(
        "difficultyLevels", ["Beginner", "Intermediate", "Advanced"]
    )

    payloads: List[PromptPayload] = []
    for lo in _learning_objective_descriptions(data):
        for qtype in question_types:
            for level in difficulties:
                if qtype == "MULTIPLE_CHOICE_MULTI_SELECT":
                    correct_count = max(1, min(num_correct, 3))
                    intermediate_format = RES_FORMAT_MULTI_SELECT.strip()
                    response_format = RES_FORMAT_MULTI_SELECT.strip()
                else:
                    correct_count = num_correct
                    intermediate_format = INTERMEDIATE_FORMAT_MCQ.strip()
                    response_format = RES_FORMAT.strip()
                incorrect_count = num_incorrect
                
                # Create multiple payloads for this configuration
                for set_idx in range(sets_per_config):
                    # Calculate questions for this specific set
                    remaining_questions = number_of_questions - (set_idx * questions_per_set)
                    questions_this_set = min(questions_per_set, remaining_questions)
                    
                    if questions_this_set <= 0:
                        continue
                    
                    payloads.append(
                        {
                            "learningObjective": lo,
                            "difficultyLevel": level,
                            "questionType": qtype,
                            "sourceText": source_text,
                            "numCorrectOptions": correct_count,
                            "numIncorrectOptions": incorrect_count,
                            "numberOfQuestions": questions_this_set,
                            "intermediateFormat": intermediate_format,
                            "responseFormat": response_format,
                            "systemPrompt": SYSTEM_CONTRACT.strip(),
                            "userPrompt": "",
                            "baseUserPrompt": "",
                        }
                    )

    state["prompt_payloads"] = payloads
    logger.info("Built %s prompt payloads", len(payloads))
    
    state["prompt_payloads"] = payloads
    return state


def _run_decomposed_node(
    client: Any, deployment: str, node_prompt: str, payload_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Helper to run a single decomposed generation node with SYSTEM_CONTRACT."""
    user_message_parts = []
    for key, value in payload_dict.items():
        if value:
            user_message_parts.append(f"{key}: {value}")
    user_message = "\n".join(user_message_parts)
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_CONTRACT + "\n\n" + node_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON from model: %s", exc)
        return {"error": "Invalid JSON", "raw": content}
    if not isinstance(parsed, dict):
        return {"error": "Non-object JSON from model", "raw": content}
    return parsed


def build_scenario(state: GraphState) -> GraphState:
    """Node 1: Generate scenario with decision point (for Intermediate/Advanced)."""
    logger.info("Building scenarios for decomposed generation")
    client = build_client()
    deployment = get_deployment_name()
    
    scenarios: List[Dict[str, Any]] = []
    for payload in state["prompt_payloads"]:
        scenario_payload = {
            "learning_objective": payload["learningObjective"],
            "difficulty": payload["difficultyLevel"],
            "source_context": payload.get("sourceText", ""),
        }
        scenario_result = _run_decomposed_node(
            client, deployment, SCENARIO_GENERATION_PROMPT, scenario_payload
        )
        scenarios.append(
            {
                "payload": payload,
                "scenario": scenario_result.get("scenario", ""),
                "decisionPoint": scenario_result.get("decisionPoint", ""),
            }
        )
    
    state["scenarios"] = scenarios
    logger.info("Built %s scenarios", len(scenarios))
    
    state["scenarios"] = scenarios
    logger.info("Built %s scenarios", len(scenarios))
    return state


def build_question(state: GraphState) -> GraphState:
    """Node 2: Generate question text based on scenario."""
    logger.info("Building questions for decomposed generation")
    client = build_client()
    deployment = get_deployment_name()
    
    questions: List[Dict[str, Any]] = []
    for scenario_data in state["scenarios"]:
        payload = scenario_data["payload"]
        question_payload = {
            "learning_objective": payload["learningObjective"],
            "difficulty": payload["difficultyLevel"],
            "scenario": scenario_data.get("scenario", ""),
            "decision_point": scenario_data.get("decisionPoint", ""),
        }
        question_result = _run_decomposed_node(
            client, deployment, QUESTION_GENERATION_PROMPT, question_payload
        )
        questions.append(
            {
                **scenario_data,
                "questionText": question_result.get("questionText", ""),
            }
        )
    
    state["questions"] = questions
    logger.info("Built %s questions", len(questions))
    
    # Log step output
    state["questions"] = questions
    logger.info("Built %s questions", len(questions))
    return state


def build_options(state: GraphState) -> GraphState:
    """Node 3: Generate answer options for each question."""
    logger.info("Building options for decomposed generation")
    client = build_client()
    deployment = get_deployment_name()
    
    outputs: List[Dict[str, Any]] = []
    for question_data in state["questions"]:
        payload = question_data["payload"]
        options_payload = {
            "question_text": question_data.get("questionText", ""),
            "scenario": question_data.get("scenario", ""),
            "num_correct": payload["numCorrectOptions"],
            "num_incorrect": payload["numIncorrectOptions"],
        }
        options_result = _run_decomposed_node(
            client, deployment, OPTIONS_GENERATION_PROMPT, options_payload
        )
        
        # Format as v1 expects
        formatted_result = {
            "LearningObjective": payload["learningObjective"],
            "questions": [
                {
                    "questionText": question_data.get("questionText", ""),
                    "answer": options_result.get("answers", []),
                    "scenarioFocus": question_data.get("scenario", ""),
                }
            ]
        }
        
        outputs.append(
            {
                "payload": payload,
                "result": formatted_result,
                "quality": {"score": 100, "issues": [], "pass": True},  # Will be validated later
                "relevancy": {"score": 100, "issues": [], "pass": True},
            }
        )
    
    state["raw_outputs"] = outputs
    logger.info("Built %s complete question packages", len(outputs))
    
    
    state["raw_outputs"] = outputs
    logger.info("Built %s full question outputs", len(outputs))
    return state


def improve_distractors(state: GraphState) -> GraphState:
    logger.info("Improving distractors")
    client = build_client()
    deployment = get_deployment_name()
    improved: List[Dict[str, Any]] = []
    for item in state["raw_outputs"]:
        payload = item["payload"]
        result = item["result"]
        if "error" in result:
            improved.append(item)
            continue
        improved.append(_improve_single_output(client, deployment, payload, result))

    state["improved_outputs"] = improved
    logger.info("Improved %s outputs", len(improved))
    
    
    state["improved_outputs"] = improved
    logger.info("Improved %s outputs", len(improved))
    return state


def _is_valid_format(result: Any, question_type: str) -> bool:
    if isinstance(result, list) and result and isinstance(result[0], dict):
        result = result[0]
    if not isinstance(result, dict):
        return False
    questions = result.get("questions")
    if not isinstance(questions, list) or not questions:
        return False
    for question in questions:
        if not isinstance(question, dict):
            return False
        if "question" not in question and "questionText" not in question:
            return False
        answers = question.get("answers") or question.get("answer")
        if not isinstance(answers, list) or not answers:
            return False
        for ans in answers:
            if not isinstance(ans, dict):
                return False
            has_answer = "answer" in ans or "answerText" in ans
            has_correct = "correct" in ans or "isCorrect" in ans
            if not has_answer or "explanation" not in ans or not has_correct:
                return False
    return True


def _count_questions(result: Any) -> int:
    if not isinstance(result, dict):
        return 0
    questions = result.get("questions")
    if not isinstance(questions, list):
        return 0
    return len(questions)


def _extract_mcq_parts(question: Dict[str, Any]) -> Dict[str, Any]:
    answers = question.get("answers") or question.get("answer") or []
    correct_answers = [
        a.get("answer") or a.get("answerText")
        for a in answers
        if a.get("correct") is True or a.get("isCorrect") is True
    ]
    distractors = [
        a.get("answer") or a.get("answerText")
        for a in answers
        if a.get("correct") is False or a.get("isCorrect") is False
    ]
    return {
        "answers": answers,
        "correct_answers": [a for a in correct_answers if a],
        "distractors": [d for d in distractors if d],
    }


def _count_result_questions(result: Any) -> int:
    if isinstance(result, list) and result and isinstance(result[0], dict):
        result = result[0]
    if isinstance(result, dict):
        questions = result.get("questions")
        if isinstance(questions, list):
            return len(questions)
    return 0


def _improve_single_output(
    client, deployment: str, payload: Dict[str, Any], result: Any
) -> Dict[str, Any]:
    prompt = USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS.replace(
        "{question}", json.dumps(result)
    ).replace("{res_format_multi_select_single_difficulty}", payload["intermediateFormat"])

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError:
        parsed = {"error": "Invalid JSON from model", "raw": content}
    return {"payload": payload, "result": parsed}


def evaluate_quality(
    client, deployment: str, result: Any, rubric: str, threshold: int
) -> Dict[str, Any]:
    if "error" in result:
        return {"score": 0, "issues": ["Invalid JSON"], "pass": False}
    prompt = USER_PROMPT_TEMPLATE_QUALITY_CHECK.replace("{rubric}", rubric).replace(
        "{questions}", json.dumps(result)
    ).replace("{threshold}", str(threshold))
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_QUALITY_CHECK},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError:
        parsed = {"score": 0, "issues": ["Invalid quality JSON"], "pass": False}
    if parsed.get("score", 0) < threshold:
        parsed["pass"] = False
    else:
        parsed["pass"] = True
    return parsed


def evaluate_relevancy(
    client,
    deployment: str,
    result: Any,
    learning_objectives: List[str],
    threshold: int,
) -> Dict[str, Any]:
    if "error" in result:
        return {"score": 0, "issues": ["Invalid JSON"], "pass": False}
    prompt = USER_PROMPT_TEMPLATE_RELEVANCY_CHECK.replace(
        "{learning_objectives}", json.dumps(learning_objectives)
    ).replace("{questions}", json.dumps(result)).replace("{threshold}", str(threshold))
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_RELEVANCY_CHECK},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError:
        parsed = {"score": 0, "issues": ["Invalid relevancy JSON"], "pass": False}
    parsed["pass"] = parsed.get("score", 0) >= threshold
    return parsed


def _review_with_prompt(
    client,
    deployment: str,
    system_prompt: str,
    user_prompt: str,
) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError:
        parsed = {"pass": False, "issues": ["Invalid reviewer JSON"]}
    if "pass" not in parsed:
        parsed["pass"] = False
    return parsed


def review_items(state: GraphState) -> GraphState:
    client = build_client()
    deployment = get_deployment_name()
    reviewed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for item in state.get("improved_outputs", []):
        payload = item["payload"]
        result = item["result"]
        reviewer_issues: List[str] = []
        questions = None
        if isinstance(result, dict):
            questions = result.get("questions")
        elif isinstance(result, list) and result and isinstance(result[0], dict):
            questions = result[0].get("questions")
        if not isinstance(questions, list):
            continue
        for question in questions:
            if not isinstance(question, dict):
                continue
            diff_prompt = USER_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY.replace(
                "{difficulty_level}", str(payload.get("difficultyLevel"))
            ).replace("{learning_objective}", payload.get("learningObjective", "")).replace(
                "{question_json}", json.dumps(question)
            ).replace("{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()).replace(
                "{rubric}", DEFAULT_QUALITY_RUBRIC.strip()
            )
            diff_system = SYSTEM_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY.replace(
                "{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()
            ).replace("{rubric}", DEFAULT_QUALITY_RUBRIC.strip())
            diff_review = _review_with_prompt(client, deployment, diff_system, diff_prompt)
            reviewer_issues.extend(diff_review.get("issues") or [])

            options = question.get("answers") or question.get("answer") or []
            correct_answers = [
                a.get("answer") or a.get("answerText")
                for a in options
                if a.get("correct") is True or a.get("isCorrect") is True
            ]
            dist_prompt = USER_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS.replace(
                "{question}", question.get("question") or question.get("questionText") or ""
            ).replace("{options}", json.dumps(options)).replace(
                "{correct_answer}", json.dumps(correct_answers)
            ).replace("{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()).replace(
                "{rubric}", DEFAULT_QUALITY_RUBRIC.strip()
            )
            dist_system = SYSTEM_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS.replace(
                "{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()
            ).replace("{rubric}", DEFAULT_QUALITY_RUBRIC.strip())
            dist_review = _review_with_prompt(client, deployment, dist_system, dist_prompt)
            reviewer_issues.extend(dist_review.get("issues") or [])

            tt_prompt = USER_PROMPT_TEMPLATE_REVIEWER_TESTTAKER.replace(
                "{question_json}", json.dumps(question)
            ).replace("{learning_objective}", payload.get("learningObjective", "")).replace(
                "{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()
            ).replace("{rubric}", DEFAULT_QUALITY_RUBRIC.strip())
            tt_system = SYSTEM_PROMPT_TEMPLATE_REVIEWER_TESTTAKER.replace(
                "{bloom_alignment}", BLOOM_ALIGNMENT_GENERATION_GUIDANCE.strip()
            ).replace("{rubric}", DEFAULT_QUALITY_RUBRIC.strip())
            tt_review = _review_with_prompt(client, deployment, tt_system, tt_prompt)
            reviewer_issues.extend(tt_review.get("issues") or [])

        entry = {
            "payload": payload,
            "result": result,
            "issues": reviewer_issues,
        }
        reviewed.append(entry)
        if reviewer_issues:
            failed.append(entry)

    state["reviewed_outputs"] = reviewed
    state["review_failed"] = failed
    return state


# REMOVED: review_after_distractors - redundant with strict distractor validation
# Distractor validation with 80% threshold is sufficient; no need for additional review step


# REMOVED: review_after_quality - redundant with strict quality validation
# Quality validation with rubric evaluation and relevancy checks is sufficient


def evaluate_distractor_quality(
    client, deployment: str, question: Dict[str, Any], learning_objective: str
) -> Dict[str, Any]:
    parts = _extract_mcq_parts(question)
    prompt = USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY.replace(
        "{question}", question.get("question", "")
    ).replace(
        "{correct_answer}", json.dumps(parts["correct_answers"])
    ).replace(
        "{distractors}", json.dumps(parts["distractors"])
    ).replace(
        "{learning_objective}", learning_objective
    ).replace(
        "{skill_or_construct}", learning_objective
    )
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_DISTRACTOR_QUALITY},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    try:
        parsed = _parse_json(content)
        # Log detailed validation results for debugging
        verdict = parsed.get("verdict", "UNKNOWN")
        notes = parsed.get("overallNotes", "No notes")
        logger.info(
            "Distractor evaluation: verdict=%s, notes=%s",
            verdict,
            notes[:100] if notes else "None"
        )
    except json.JSONDecodeError:
        parsed = {"verdict": "FAIL", "overallNotes": "Invalid distractor quality JSON"}
        logger.warning("Failed to parse distractor quality evaluation response")
    return parsed


def validate_distractors(state: GraphState) -> GraphState:
    logger.info("Validating distractor quality")
    client = build_client()
    deployment = get_deployment_name()
    
    # Get already passed items (accumulated across correction loops)
    already_passed = state.get("distractor_validation_passed", [])
    
    # Items to validate: everything in improved_outputs (only failed items from corrections)
    items_to_validate = state["improved_outputs"]
    
    passed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    
    for item in items_to_validate:
        payload = item["payload"]
        result = item["result"]
        
        if "error" in result:
            passed.append(item)
            continue
        questions = result.get("questions")
        if not isinstance(questions, list):
            passed.append(item)
            continue
        passed_questions: List[Dict[str, Any]] = []
        failed_questions: List[Dict[str, Any]] = []
        for idx, question in enumerate(questions):
            if not isinstance(question, dict):
                passed_questions.append({"index": idx, "question": question})
                continue
            evaluation = evaluate_distractor_quality(
                client, deployment, question, payload["learningObjective"]
            )
            
            # Apply 80% threshold logic
            verdict = evaluation.get("verdict", "FAIL")
            distractors_data = evaluation.get("distractors", [])
            
            # Check if at least 80% of distractors pass
            total_distractors = len(distractors_data)
            passed_distractors = sum(1 for d in distractors_data if d.get("pass", False))
            
            # Calculate 80% threshold (round up)
            required_pass_count = max(1, int(0.8 * total_distractors + 0.99))
            
            # Override verdict if 80% threshold is met
            if passed_distractors >= required_pass_count and total_distractors > 0:
                meets_threshold = True
            else:
                meets_threshold = False
            
            # Pass if: original verdict is PASS OR meets 80% threshold
            if verdict == "PASS" or meets_threshold:
                passed_questions.append({"index": idx, "question": question})
                logger.info("Question %s PASSED distractor validation", idx)
                continue
                
            failure_reasons = [evaluation.get("overallNotes") or "Distractor quality failed."]
            for entry in evaluation.get("distractors", []):
                reason = entry.get("failReason")
                if reason:
                    failure_reasons.append(reason)
            logger.info(
                "Question %s FAILED distractor validation: %s",
                idx,
                "; ".join(failure_reasons)[:200]
            )
            failed_questions.append(
                {
                    "index": idx,
                    "question": question,
                    "failure_reasons": [r for r in failure_reasons if r],
                }
            )
        if failed_questions:
            failed.append(
                {
                    "payload": payload,
                    "result": result,
                    "passed_questions": passed_questions,
                    "failed_questions": failed_questions,
                    "question_count": len(questions),
                }
            )
        else:
            passed.append(item)
    
    # Accumulate passed items (keep growing across correction loops)
    all_passed = already_passed + passed
    
    # Update state
    state["distractor_validation_passed"] = all_passed
    state["distractor_validation_failed"] = failed
    
    # During correction loops: improved_outputs contains ONLY passed items
    # Failed items will be added at the END by routing function
    state["improved_outputs"] = all_passed
    
    logger.info(
        "Distractor validation: %s newly passed, %s total passed, %s failed", 
        len(passed), len(all_passed), len(failed)
    )
    
    state["distractor_validation_passed"] = all_passed
    state["distractor_validation_failed"] = failed
    state["improved_outputs"] = all_passed
    logger.info(
        "Distractor validation: %s passed (newly: %s), %s failed",
        len(all_passed), len(passed), len(failed)
    )
    return state


def correct_distractors(state: GraphState) -> GraphState:
    logger.info("Correcting failed distractors")
    client = build_client()
    deployment = get_deployment_name()
    corrected_failed: List[Dict[str, Any]] = []
    for item in state.get("distractor_validation_failed", []):
        payload = item["payload"]
        result = item["result"]
        passed_questions = {
            entry["index"]: entry["question"] for entry in item.get("passed_questions", [])
        }
        question_count = item.get("question_count") or 0
        for failed_entry in item.get("failed_questions", []):
            question = failed_entry.get("question")
            failure_text = "\n".join(
                failed_entry.get("failure_reasons") or ["Distractor quality failed."]
            )
            if not isinstance(question, dict):
                continue
            logger.info(
                "Correcting distractor for question at index %s due to: %s",
                failed_entry.get("index", "?"),
                failure_text[:150]
            )
            correction_prompt = USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION.replace(
                "{failure_reasons}", failure_text
            ).replace(
                "{question_json}", json.dumps({"questions": [question]})
            ).replace(
                "{response_format}", payload["intermediateFormat"]
            )
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
                    },
                    {"role": "user", "content": correction_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            try:
                corrected = _parse_json(content)
                corrected_questions = corrected.get("questions")
                if isinstance(corrected_questions, list) and corrected_questions:
                    passed_questions[failed_entry["index"]] = corrected_questions[0]
                else:
                    passed_questions[failed_entry["index"]] = question
            except json.JSONDecodeError:
                passed_questions[failed_entry["index"]] = question

        if question_count <= 0:
            original_questions = result.get("questions")
            if isinstance(original_questions, list):
                question_count = len(original_questions)
        rebuilt = [passed_questions.get(idx) for idx in range(question_count)]
        original_questions = result.get("questions")
        if isinstance(original_questions, list):
            for idx, entry in enumerate(rebuilt):
                if entry is None and idx < len(original_questions):
                    rebuilt[idx] = original_questions[idx]
        result["questions"] = rebuilt
        corrected_failed.append({"payload": payload, "result": result})

    # Send ONLY corrected items back for re-validation
    # Previously passed items don't need re-validation
    state["improved_outputs"] = corrected_failed
    state["distractor_validation_failed"] = []
    state["distractor_correction_attempts"] = state.get(
        "distractor_correction_attempts", 0
    ) + 1
    logger.info("Corrected %s failed outputs", len(corrected_failed))
    return state


def validate_and_fix_format(state: GraphState) -> GraphState:
    logger.info("Validating output format")
    client = build_client()
    deployment = get_deployment_name()
    fixed: List[Dict[str, Any]] = []
    all_valid = True
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        if not _is_valid_format(result, payload["questionType"]):
            all_valid = False
            logger.info("Format invalid, attempting repair for %s", payload["questionType"])
            prompt = USER_PROMPT_TEMPLATE_FIX_FORMAT.replace(
                "{res_format}", payload["intermediateFormat"]
            ).replace("{raw_output}", json.dumps(result))
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            try:
                result = _parse_json(content)
            except json.JSONDecodeError:
                result = {"error": "Invalid JSON from model", "raw": content}

        prompt = USER_PROMPT_TEMPLATE_FIX_FORMAT.replace(
            "{res_format}", payload["responseFormat"]
        ).replace("{raw_output}", json.dumps(result))
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = _parse_json_raw(content)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from model", "raw": content}
        fixed.append({"payload": payload, "result": parsed})

    state["improved_outputs"] = fixed
    logger.info("Format validation complete for %s outputs", len(fixed))
    state["format_fix_attempts"] = state.get("format_fix_attempts", 0) + 1
    max_attempts = state["input"].get("maxFormatFixAttempts", 2)
    state["format_loop"] = (not all_valid) and state["format_fix_attempts"] < max_attempts
    return state


def validate_quality(state: GraphState) -> GraphState:
    logger.info("Validating quality and relevancy")
    client = build_client()
    deployment = get_deployment_name()
    rubric = state["input"].get("qualityRubric") or DEFAULT_QUALITY_RUBRIC.strip()
    threshold = state["input"].get("qualityThreshold", 85)
    relevancy_threshold = state["input"].get("relevancyThreshold", 85)
    learning_objectives = _learning_objective_descriptions(state["input"])

    # Get already passed items (accumulated across correction loops)
    already_passed = state.get("quality_validation_passed", [])
    
    # Items to validate: everything in improved_outputs (only failed items from corrections)
    items_to_validate = state["improved_outputs"]
    
    passed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    
    for item in items_to_validate:
        payload = item["payload"]
        result = item["result"]
        
        quality = evaluate_quality(client, deployment, result, rubric, threshold)
        relevancy = evaluate_relevancy(
            client, deployment, result, learning_objectives, relevancy_threshold
        )
        entry = {
            "payload": payload,
            "result": result,
            "quality": quality,
            "relevancy": relevancy,
        }
        if quality.get("pass") and relevancy.get("pass"):
            passed.append(entry)
        else:
            failed.append(entry)
    
    # Accumulate passed items (keep growing across correction loops)
    all_passed = already_passed + passed
    
    # Update state
    state["quality_validation_passed"] = all_passed
    state["quality_validation_failed"] = failed
    
    # During correction loops: improved_outputs contains ONLY passed items
    # Failed items will be added at the END by routing function
    state["improved_outputs"] = [
        {"payload": entry["payload"], "result": entry["result"]}
        for entry in all_passed
    ]
    
    logger.info(
        "Quality validation: %s newly passed, %s total passed, %s failed",
        len(passed), len(all_passed), len(failed)
    )
    
    state["quality_validation_passed"] = all_passed
    state["quality_validation_failed"] = failed
    state["improved_outputs"] = all_passed
    logger.info(
        "Quality validation: %s passed (newly: %s), %s failed",
        len(all_passed), len(passed), len(failed)
    )
    return state


def correct_quality(state: GraphState) -> GraphState:
    logger.info("Correcting failed quality or relevancy")
    client = build_client()
    deployment = get_deployment_name()
    corrected_failed: List[Dict[str, Any]] = []
    for item in state.get("quality_validation_failed", []):
        payload = item["payload"]
        result = item["result"]
        quality = item.get("quality", {})
        relevancy = item.get("relevancy", {})
        failure_reasons: List[str] = []
        if not quality.get("pass"):
            issues = quality.get("issues") or []
            issue_text = "; ".join(
                [issue if isinstance(issue, str) else json.dumps(issue) for issue in issues]
            )
            failure_reasons.append("Quality issues: " + issue_text)
        if not relevancy.get("pass"):
            issues = relevancy.get("issues") or []
            issue_text = "; ".join(
                [issue if isinstance(issue, str) else json.dumps(issue) for issue in issues]
            )
            failure_reasons.append("Relevancy issues: " + issue_text)
        failure_reason_text = "\n".join([r for r in failure_reasons if r]) or "Failed evaluation."

        correction_prompt = USER_PROMPT_TEMPLATE_CORRECTION.replace(
            "{learning_obj}", payload["learningObjective"]
        ).replace("{difficulty_level}", payload["difficultyLevel"]).replace(
            "{question_type}", payload["questionType"]
        ).replace(
            "{failure_reasons}", failure_reason_text
        ).replace(
            "{question_json}", json.dumps(result)
        ).replace(
            "{response_format}", payload["intermediateFormat"]
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": payload["systemPrompt"]},
                {"role": "user", "content": correction_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            corrected = _parse_json(content)
        except json.JSONDecodeError:
            corrected = {"error": "Invalid JSON from model", "raw": content}
        corrected_failed.append({"payload": payload, "result": corrected})

    # Send ONLY corrected items back for re-validation
    # Previously passed items don't need re-validation
    state["improved_outputs"] = corrected_failed
    state["quality_validation_failed"] = []
    state["quality_correction_attempts"] = state.get("quality_correction_attempts", 0) + 1
    logger.info("Corrected %s failed quality outputs", len(corrected_failed))
    return state


def format_conversion(state: GraphState) -> GraphState:
    logger.info("Formatting results")
    client = build_client()
    deployment = get_deployment_name()
    formatted: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        prompt = USER_PROMPT_TEMPLATE_FIX_FORMAT.replace(
            "{res_format}", payload["responseFormat"]
        ).replace("{raw_output}", json.dumps(result))
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = _parse_json_raw(content)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from model", "raw": content}
        formatted.append(
            {
                "payload": payload,
                "learningObjective": payload["learningObjective"],
                "difficultyLevel": payload["difficultyLevel"],
                "questionType": payload["questionType"],
                "result": parsed,
            }
        )
    state["formatted"] = formatted
    logger.info("Formatted %s outputs", len(formatted))
    return state


def _route_from_improve(state: GraphState) -> str:
    return "validate_distractors"


def _route_from_validate_distractors(state: GraphState) -> str:
    failed = state.get("distractor_validation_failed", [])
    max_attempts = state["input"].get(
        "maxDistractorFixAttempts", state["input"].get("maxAttempts", 6)
    )
    attempts = state.get("distractor_correction_attempts", 0)
    
    # If there are failures and we haven't hit max attempts, go to correction
    if failed and attempts < max_attempts:
        return "correct_distractors"
    
    # Max attempts reached or no failures
    # NOW add failed items to improved_outputs (they've been improved through multiple attempts)
    if failed:
        logger.info(
            "Max distractor correction attempts (%s) reached. Including %s failed items for quality validation.",
            max_attempts, len(failed)
        )
        passed_outputs = state.get("distractor_validation_passed", [])
        failed_outputs = [{"payload": item["payload"], "result": item["result"]} for item in failed]
        state["improved_outputs"] = passed_outputs + failed_outputs
    
    # Proceed to quality validation with all items (passed + failed)
    return "validate_quality"


def _route_from_validate_quality(state: GraphState) -> str:
    failed = state.get("quality_validation_failed", [])
    max_attempts = state["input"].get(
        "maxQualityFixAttempts", state["input"].get("maxAttempts", 6)
    )
    attempts = state.get("quality_correction_attempts", 0)
    
    # If there are failures and we haven't hit max attempts, go to correction
    if failed and attempts < max_attempts:
        return "correct_quality"
    
    # Max attempts reached or no failures
    # NOW add failed items to improved_outputs (they've been improved through multiple attempts)
    if failed:
        logger.info(
            "Max quality correction attempts (%s) reached. Including %s failed items in final output.",
            max_attempts, len(failed)
        )
        passed_outputs = [
            {"payload": entry["payload"], "result": entry["result"]}
            for entry in state.get("quality_validation_passed", [])
        ]
        failed_outputs = [{"payload": entry["payload"], "result": entry["result"]} for entry in failed]
        state["improved_outputs"] = passed_outputs + failed_outputs
    
    # Proceed to end with all items (passed + failed)
    return "end"


def build_graph():
    graph = StateGraph[GraphState, None, GraphState, GraphState](GraphState)
    graph.add_node("build_prompts", build_prompt_payloads)
    graph.add_node("build_scenario", build_scenario)
    graph.add_node("build_question", build_question)
    graph.add_node("build_options", build_options)
    graph.add_node("improve", improve_distractors)
    graph.add_node("validate_distractors", validate_distractors)
    graph.add_node("correct_distractors", correct_distractors)
    graph.add_node("validate_quality", validate_quality)
    graph.add_node("correct_quality", correct_quality)
    
    graph.set_entry_point("build_prompts")
    
    graph.add_edge("build_prompts", "build_scenario")
    graph.add_edge("build_scenario", "build_question")
    graph.add_edge("build_question", "build_options")
    graph.add_edge("build_options", "improve")
    graph.add_conditional_edges(
        "improve",
        _route_from_improve,
        {"validate_distractors": "validate_distractors", "validate_quality": "validate_quality"},
    )
    graph.add_conditional_edges(
        "validate_distractors",
        _route_from_validate_distractors,
        {
            "correct_distractors": "correct_distractors",
            "validate_quality": "validate_quality",
        },
    )
    graph.add_edge("correct_distractors", "validate_distractors")
    graph.add_conditional_edges(
        "validate_quality",
        _route_from_validate_quality,
        {"correct_quality": "correct_quality", "end": END},
    )
    graph.add_edge("correct_quality", "validate_quality")
    return graph.compile()


def _fill_missing_questions(
    app, payload: PipelineInput, final_state: Dict[str, Any]
) -> Dict[str, Any]:
    max_fill_attempts = payload.get("maxFillAttempts", 1)
    if max_fill_attempts < 1:
        return final_state
    target_count = payload.get("numberOfQuestions", 3)
    missing_sections: List[Dict[str, Any]] = []
    for item in final_state.get("improved_outputs", []):
        result = item.get("result")
        current_count = _count_result_questions(result)
        if current_count < target_count:
            missing_sections.append(
                {
                    "item": item,
                    "missing": target_count - current_count,
                }
            )
    if not missing_sections:
        return final_state

    for entry in missing_sections:
        item = entry["item"]
        missing = entry["missing"]
        scoped_payload: PipelineInput = dict(payload)
        scoped_payload["learningObjectives"] = [item["payload"]["learningObjective"]]
        scoped_payload["questionTypes"] = [item["payload"]["questionType"]]
        scoped_payload["difficultyLevels"] = [item["payload"]["difficultyLevel"]]
        scoped_payload["numberOfQuestions"] = missing

        scoped_state = app.invoke(
            {
                "input": scoped_payload,
                "prompt_payloads": [],
                "raw_outputs": [],
                "improved_outputs": [],
                "formatted": [],
            }
        )
        new_entries = scoped_state.get("improved_outputs", [])
        if not new_entries:
            continue
        new_result = new_entries[0].get("result")
        if isinstance(new_result, list) and new_result and isinstance(new_result[0], dict):
            new_result = new_result[0]
        if not isinstance(new_result, dict):
            continue
        new_questions = new_result.get("questions")
        if not isinstance(new_questions, list) or not new_questions:
            continue

        current_result = item.get("result")
        if isinstance(current_result, list) and current_result and isinstance(current_result[0], dict):
            current_result = current_result[0]
        if not isinstance(current_result, dict):
            continue
        current_questions = current_result.get("questions")
        if not isinstance(current_questions, list):
            continue
        current_result["questions"] = current_questions + new_questions

    return final_state


def _build_output(payload: PipelineInput, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_los = _normalize_learning_objectives(payload)
    lo_index = {entry["description"]: entry for entry in normalized_los}

    objectives_out: List[Dict[str, Any]] = []
    for idx, entry in enumerate(normalized_los, start=1):
        objectives_out.append(
            {
                "learningObjective": entry.get("description", ""),
                "learningObjectiveUuid": entry.get("id"),
                "learningObjectiveOrder": idx,
                "questions": [],
            }
        )

    for item in items:
        payload_item = item.get("payload", {})
        lo_text = payload_item.get("learningObjective") or item.get("learningObjective")
        objective = next(
            (obj for obj in objectives_out if obj.get("learningObjective") == lo_text), None
        )
        if not objective:
            continue
        result = item.get("result")
        questions = []
        if isinstance(result, dict):
            questions = result.get("questions") or []
        elif isinstance(result, list) and result and isinstance(result[0], dict):
            questions = result[0].get("questions") or []
        for question in questions:
            question_type = payload_item.get("questionType") or item.get("questionType")
            answers_out: List[Dict[str, Any]] = []
            scenario_focus = None
            answer_items = []
            if isinstance(question, dict):
                answer_items = question.get("answers") or question.get("answer") or []
            for answer in answer_items:
                answers_out.append(
                    {
                        "answerId": str(uuid4()),
                        "answerText": answer.get("answer") or answer.get("answerText"),
                        "explanation": answer.get("explanation"),
                        "isCorrect": (
                            answer.get("correct")
                            if answer.get("correct") is not None
                            else answer.get("isCorrect")
                        ),
                    }
                )
            if isinstance(question, dict):
                scenario_focus = (
                    question.get("scenarioFocus")
                    or question.get("context")
                    or question.get("learningObjective")
                    or question.get("LearningObjective")
                )
            objective["questions"].append(
                {
                    "id": str(uuid4()),
                    "questionType": question_type,
                    "aiGeneratedDifficulty": payload_item.get("difficultyLevel")
                    or item.get("difficultyLevel"),
                    "questionText": (
                        question.get("questionText") or question.get("question")
                        if isinstance(question, dict)
                        else None
                    ),
                    "answer": answers_out,
                    "isUploaded": False,
                    "scenarioFocus": scenario_focus,
                }
            )

    data_learning_objectives = []
    for entry in normalized_los:
        data_learning_objectives.append(
            {"id": entry.get("id"), "description": entry.get("description", "")}
        )

    return {
        "learningObjectives": objectives_out,
        "questionGenerationStatus": "READY_FOR_REVIEW",
    }


def run_pipeline(payload: PipelineInput) -> Dict[str, Any]:
    app = build_graph()
    final_state = app.invoke(
        {
            "input": payload,
            "prompt_payloads": [],
            "scenarios": [],
            "questions": [],
            "raw_outputs": [],
            "improved_outputs": [],
            "formatted": [],
        }
    )
    
    # Post-graph processing: format conversion and validation
    # REMOVED: _fill_missing_questions - causing infinite loops with per-question payloads
    final_state = format_conversion(final_state)
    final_state = validate_and_fix_format(final_state)
    
    # Retry format fix if needed
    if final_state.get("format_loop"):
        final_state = format_conversion(final_state)
        final_state = validate_and_fix_format(final_state)
    output = _build_output(payload, final_state.get("improved_outputs", []))
    
    logger.info("Pipeline complete: generated questions for %s LOs", 
                len(output.get("learningObjectives", [])))
    return output
