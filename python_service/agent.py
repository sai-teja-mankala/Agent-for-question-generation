import json
import logging
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph

from .llm import build_client, get_deployment_name
from .prompts import (
    INTERMEDIATE_FORMAT_MATCHING,
    INTERMEDIATE_FORMAT_MCQ,
    RES_FORMAT,
    RES_FORMAT_MATCH_COLUMNS,
    RES_FORMAT_MULTI_SELECT,
    SYSTEM_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    SYSTEM_PROMPT_TEMPLATE_QUALITY_CHECK,
    SYSTEM_PROMPT_TEMPLATE_RELEVANCY_CHECK,
    SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT,
    SYSTEM_PROMPT_TEMPLATE_IMPROVE_MATCHING,
    SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS,
    SYSTEM_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_FIX_FORMAT,
    USER_PROMPT_TEMPLATE_IMPROVE_MATCHING,
    USER_PROMPT_TEMPLATE_MATCH_COLUMNS,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    USER_PROMPT_TEMPLATE_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_QUALITY_CHECK,
    USER_PROMPT_TEMPLATE_RELEVANCY_CHECK,
    USER_PROMPT_TEMPLATE_MATCH_COLUMNS,
)
from .qg_types import GraphState, LevelOfQuiz, PipelineInput, PromptPayload, QuestionType

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




def build_prompt_payloads(state: GraphState) -> GraphState:
    data = state["input"]
    logger.info("Building prompt payloads")
    locale = data.get("locale", "en")
    source_text = data.get("sourceText", "")
    number_of_questions = data.get("numberOfQuestions", 3)
    question_types = data.get("questionTypes", ["MULTIPLE_CHOICE"])
    num_correct = data.get("numCorrectOptions", 1)
    num_incorrect = data.get("numIncorrectOptions", 3)
    difficulties: List[LevelOfQuiz] = data.get(
        "difficultyLevels", ["Beginner", "Intermediate", "Advanced"]
    )

    payloads: List[PromptPayload] = []
    for lo in data.get("learningObjectives", []):
        for qtype in question_types:
            for level in difficulties:
                if qtype == "MATCHING":
                    system_prompt = SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
                        "{locale}", locale
                    )
                    user_prompt = (
                        USER_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
                            "{difficulty_level}", level
                        )
                        .replace("{source_text}", source_text)
                        .replace("{learning_obj}", lo)
                        .replace("{number_of_questions}", str(number_of_questions))
                        .replace("{num_correct_options}", str(num_correct))
                        .replace("{num_incorrect_options}", str(num_incorrect))
                        .replace("{intermediate_format}", INTERMEDIATE_FORMAT_MATCHING)
                    )
                    response_format = RES_FORMAT_MATCH_COLUMNS
                    intermediate_format = INTERMEDIATE_FORMAT_MATCHING
                else:
                    response_format = (
                        RES_FORMAT_MULTI_SELECT
                        if qtype == "MULTIPLE_CHOICE_MULTI_SELECT"
                        else RES_FORMAT
                    )
                    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace(
                        "{locale}", locale
                    ).replace("{num_correct_options}", str(num_correct)).replace(
                        "{num_incorrect_options}", str(num_incorrect)
                    )
                    user_prompt = (
                        USER_PROMPT_TEMPLATE.replace(
                            "{difficulty_level}", level
                        )
                        .replace("{source_text}", source_text)
                        .replace("{learning_obj}", lo)
                        .replace("{number_of_questions}", str(number_of_questions))
                        .replace("{num_correct_options}", str(num_correct))
                        .replace("{num_incorrect_options}", str(num_incorrect))
                        .replace("{intermediate_format}", INTERMEDIATE_FORMAT_MCQ)
                    )
                    intermediate_format = INTERMEDIATE_FORMAT_MCQ
                payloads.append(
                    {
                        "systemPrompt": system_prompt,
                        "userPrompt": user_prompt,
                        "responseFormat": response_format,
                        "intermediateFormat": intermediate_format,
                        "learningObjective": lo,
                        "difficultyLevel": level,
                        "questionType": qtype,
                    }
                )

    state["prompt_payloads"] = payloads
    logger.info("Built %s prompt payloads", len(payloads))
    return state


def generate_questions(state: GraphState) -> GraphState:
    logger.info("Generating questions with Azure OpenAI")
    client = build_client()
    deployment = get_deployment_name()
    number_of_questions = state["input"].get("numberOfQuestions", 3)
    rubric = state["input"].get("qualityRubric", "No rubric provided.")
    threshold = state["input"].get("qualityThreshold", 85)
    relevancy_threshold = state["input"].get("relevancyThreshold", 85)
    max_attempts = state["input"].get("maxAttempts", 2)
    learning_objectives = state["input"].get("learningObjectives", [])

    outputs: List[Dict[str, Any]] = []
    for payload in state["prompt_payloads"]:
        attempt = 0
        last_result: Dict[str, Any] = {"error": "No attempts"}
        while attempt < max_attempts:
            attempt += 1
            logger.info(
                "Generating (%s/%s) for %s/%s",
                attempt,
                max_attempts,
                payload["questionType"],
                payload["difficultyLevel"],
            )
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": payload["systemPrompt"]},
                    {"role": "user", "content": payload["userPrompt"]},
                ],
            )
            content = response.choices[0].message.content or ""
            try:
                parsed = _parse_json(content)
            except json.JSONDecodeError:
                parsed = {"error": "Invalid JSON from model", "raw": content}

            last_result = parsed
            question_count = _count_questions(parsed)
            if question_count != number_of_questions:
                logger.info(
                    "Generated %s questions, expected %s. Regenerating.",
                    question_count,
                    number_of_questions,
                )
                continue
            quality = evaluate_quality(client, deployment, parsed, rubric, threshold)
            relevancy = evaluate_relevancy(
                client, deployment, parsed, learning_objectives, relevancy_threshold
            )
            if quality.get("pass") and relevancy.get("pass"):
                outputs.append(
                    {
                        "payload": payload,
                        "result": parsed,
                        "quality": quality,
                        "relevancy": relevancy,
                    }
                )
                break

            logger.info(
                "Quality or relevancy failed (q=%s, r=%s). Regenerating.",
                quality.get("score"),
                relevancy.get("score"),
            )
            failure_reasons: List[str] = []
            if not quality.get("pass"):
                issues = quality.get("issues") or []
                failure_reasons.append("Quality issues: " + "; ".join(issues))
            if not relevancy.get("pass"):
                issues = relevancy.get("issues") or []
                failure_reasons.append("Relevancy issues: " + "; ".join(issues))
            failure_reason_text = "\n".join(failure_reasons) or "Failed evaluation."
            payload["userPrompt"] = USER_PROMPT_TEMPLATE_CORRECTION.replace(
                "{learning_obj}", payload["learningObjective"]
            ).replace("{difficulty_level}", payload["difficultyLevel"]).replace(
                "{question_type}", payload["questionType"]
            ).replace(
                "{failure_reasons}", failure_reason_text
            ).replace(
                "{question_json}", json.dumps(parsed)
            ).replace(
                "{response_format}", payload["intermediateFormat"]
            )

        else:
            outputs.append(
                {
                    "payload": payload,
                    "result": last_result,
                    "quality": {"score": 0, "issues": ["Max attempts exceeded"], "pass": False},
                    "relevancy": {"score": 0, "issues": ["Max attempts exceeded"], "pass": False},
                }
            )

    state["raw_outputs"] = outputs
    logger.info("Generated %s raw outputs", len(outputs))
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

        if payload["questionType"] == "MATCHING":
            prompt = USER_PROMPT_TEMPLATE_IMPROVE_MATCHING.replace(
                "{question}", json.dumps(result)
            ).replace("{res_format_match_columns}", payload["intermediateFormat"])

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_IMPROVE_MATCHING},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            try:
                parsed = _parse_json(content)
            except json.JSONDecodeError:
                parsed = {"error": "Invalid JSON from model", "raw": content}
            improved.append({"payload": payload, "result": parsed})
            continue

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
        improved.append({"payload": payload, "result": parsed})

    state["improved_outputs"] = improved
    logger.info("Improved %s outputs", len(improved))
    return state


def _is_valid_format(result: Any, question_type: str) -> bool:
    if not isinstance(result, dict):
        return False
    questions = result.get("questions")
    if not isinstance(questions, list) or not questions:
        return False
    for question in questions:
        if not isinstance(question, dict) or "question" not in question:
            return False
        if question_type == "MATCHING":
            if "column_a_answers" not in question or "column_b_answers" not in question:
                return False
            if "answers" not in question:
                return False
        else:
            answers = question.get("answers")
            if not isinstance(answers, list) or not answers:
                return False
            for ans in answers:
                if not isinstance(ans, dict):
                    return False
                if "answer" not in ans or "explanation" not in ans or "correct" not in ans:
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
    answers = question.get("answers", [])
    correct_answers = [a.get("answer") for a in answers if a.get("correct") is True]
    distractors = [a.get("answer") for a in answers if a.get("correct") is False]
    return {
        "answers": answers,
        "correct_answers": [a for a in correct_answers if a],
        "distractors": [d for d in distractors if d],
    }


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
    except json.JSONDecodeError:
        parsed = {"verdict": "FAIL", "overallNotes": "Invalid distractor quality JSON"}
    return parsed


def validate_distractors(state: GraphState) -> GraphState:
    logger.info("Validating distractor quality")
    client = build_client()
    deployment = get_deployment_name()
    passed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        if "error" in result or payload["questionType"] == "MATCHING":
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
            if evaluation.get("verdict") == "PASS":
                passed_questions.append({"index": idx, "question": question})
                continue
            failure_reasons = [evaluation.get("overallNotes") or "Distractor quality failed."]
            for entry in evaluation.get("distractors", []):
                reason = entry.get("failReason")
                if reason:
                    failure_reasons.append(reason)
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

    state["distractor_validation_passed"] = passed
    state["distractor_validation_failed"] = failed
    state["improved_outputs"] = passed + [
        {"payload": item["payload"], "result": item["result"]} for item in failed
    ]
    logger.info(
        "Distractor validation complete: %s passed, %s failed", len(passed), len(failed)
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

    passed_outputs = state.get("distractor_validation_passed", [])
    state["improved_outputs"] = passed_outputs + corrected_failed
    state["distractor_validation_failed"] = []
    state["distractor_correction_attempts"] = state.get(
        "distractor_correction_attempts", 0
    ) + 1
    return state


def validate_and_fix_format(state: GraphState) -> GraphState:
    logger.info("Validating output format")
    client = build_client()
    deployment = get_deployment_name()
    fixed: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        if not _is_valid_format(result, payload["questionType"]):
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
            parsed = _parse_json(content)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from model", "raw": content}
        fixed.append({"payload": payload, "result": parsed})

    state["improved_outputs"] = fixed
    logger.info("Format validation complete for %s outputs", len(fixed))
    return state


def validate_quality(state: GraphState) -> GraphState:
    logger.info("Validating quality and relevancy")
    client = build_client()
    deployment = get_deployment_name()
    rubric = state["input"].get("qualityRubric", "No rubric provided.")
    threshold = state["input"].get("qualityThreshold", 85)
    relevancy_threshold = state["input"].get("relevancyThreshold", 85)
    learning_objectives = state["input"].get("learningObjectives", [])

    passed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
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

    state["quality_validation_passed"] = passed
    state["quality_validation_failed"] = failed
    state["quality"] = [
        {"payload": entry["payload"], "quality": entry["quality"], "relevancy": entry["relevancy"]}
        for entry in passed + failed
    ]
    logger.info(
        "Quality validation complete: %s passed, %s failed", len(passed), len(failed)
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
            failure_reasons.append("Quality issues: " + "; ".join(issues))
        if not relevancy.get("pass"):
            issues = relevancy.get("issues") or []
            failure_reasons.append("Relevancy issues: " + "; ".join(issues))
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

    passed_outputs = [
        {"payload": entry["payload"], "result": entry["result"]}
        for entry in state.get("quality_validation_passed", [])
    ]
    state["improved_outputs"] = passed_outputs + corrected_failed
    state["quality_validation_failed"] = []
    state["quality_correction_attempts"] = state.get("quality_correction_attempts", 0) + 1
    return state


def format_conversion(state: GraphState) -> GraphState:
    logger.info("Formatting results")
    formatted: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        formatted.append(
            {
                "learningObjective": payload["learningObjective"],
                "difficultyLevel": payload["difficultyLevel"],
                "questionType": payload["questionType"],
                "result": result,
            }
        )
    state["formatted"] = formatted
    logger.info("Formatted %s outputs", len(formatted))
    return state


def _route_from_improve(state: GraphState) -> str:
    has_mcq = any(
        item.get("payload", {}).get("questionType") != "MATCHING"
        for item in state.get("improved_outputs", [])
    )
    return "validate_distractors" if has_mcq else "validate_quality"


def _route_from_validate_distractors(state: GraphState) -> str:
    failed = state.get("distractor_validation_failed", [])
    max_attempts = state["input"].get(
        "maxDistractorFixAttempts", state["input"].get("maxAttempts", 2)
    )
    attempts = state.get("distractor_correction_attempts", 0)
    if failed and attempts < max_attempts:
        return "correct_distractors"
    return "validate_quality"


def _route_from_validate_quality(state: GraphState) -> str:
    failed = state.get("quality_validation_failed", [])
    max_attempts = state["input"].get(
        "maxQualityFixAttempts", state["input"].get("maxAttempts", 2)
    )
    attempts = state.get("quality_correction_attempts", 0)
    if failed and attempts < max_attempts:
        return "correct_quality"
    return "validate"


def build_graph():
    graph = StateGraph[GraphState, None, GraphState, GraphState](GraphState)
    graph.add_node("build_prompts", build_prompt_payloads)
    graph.add_node("generate", generate_questions)
    graph.add_node("improve", improve_distractors)
    graph.add_node("validate_distractors", validate_distractors)
    graph.add_node("correct_distractors", correct_distractors)
    graph.add_node("validate_quality", validate_quality)
    graph.add_node("correct_quality", correct_quality)
    graph.add_node("validate", validate_and_fix_format)
    graph.add_node("format", format_conversion)

    graph.set_entry_point("build_prompts")
    graph.add_edge("build_prompts", "generate")
    graph.add_edge("generate", "improve")
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
        {"correct_quality": "correct_quality", "validate": "validate"},
    )
    graph.add_edge("correct_quality", "validate_quality")
    graph.add_edge("validate", "format")
    graph.add_edge("format", END)
    return graph.compile()


def run_pipeline(payload: PipelineInput) -> Dict[str, Any]:
    app = build_graph()
    final_state = app.invoke(
        {
            "input": payload,
            "prompt_payloads": [],
            "raw_outputs": [],
            "improved_outputs": [],
            "quality": [],
            "formatted": [],
        }
    )
    learning_objectives = payload.get("learningObjectives", [])
    number_of_questions = payload.get("numberOfQuestions", 3)
    question_types = payload.get("questionTypes", ["MULTIPLE_CHOICE"])
    difficulty_levels = payload.get(
        "difficultyLevels", ["Beginner", "Intermediate", "Advanced"]
    )
    expected_total = (
        len(learning_objectives)
        * number_of_questions
        * len(question_types)
        * len(difficulty_levels)
    )
    actual_total = 0
    for item in final_state.get("formatted", []):
        result = item.get("result")
        questions = None
        if isinstance(result, dict):
            questions = result.get("questions")
        elif isinstance(result, list) and result and isinstance(result[0], dict):
            questions = result[0].get("questions")
        if isinstance(questions, list):
            actual_total += len(questions)
    final_state["summary"] = {
        "assessmentContainerId": payload.get("assessmentContainerId"),
        "internalAssessmentId": payload.get("internalAssessmentId"),
        "learningObjectiveUuid": payload.get("learningObjectiveUuid"),
        "learningObjectivesCount": len(learning_objectives),
        "numberOfQuestions": number_of_questions,
        "questionTypesCount": len(question_types),
        "difficultyLevelsCount": len(difficulty_levels),
        "expectedTotalQuestions": expected_total,
        "actualTotalQuestions": actual_total,
    }
    return final_state
