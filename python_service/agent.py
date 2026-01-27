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
    SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS,
    SYSTEM_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_FIX_FORMAT,
    USER_PROMPT_TEMPLATE_MATCH_COLUMNS,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    USER_PROMPT_TEMPLATE_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION,
    USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY,
    USER_PROMPT_TEMPLATE_QUALITY_CHECK,
    USER_PROMPT_TEMPLATE_RELEVANCY_CHECK,
)
from .qg_types import GraphState, PipelineInput, PromptPayload, QuestionType

logger = logging.getLogger("pipeline")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


_STATE_LOG_PATH = Path(__file__).resolve().parents[1] / "state_log.jsonl"
_RESULT_QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "result_questions.txt"
_FINAL_STATE_PATH = Path(__file__).resolve().parents[1] / "final_state.json"


def _append_json_line(record: Dict[str, Any], path: Path = _STATE_LOG_PATH) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    except OSError as exc:
        logger.warning("Failed to write state log: %s", exc)


def _log_state_summary(state: GraphState, stage: str) -> None:
    def _safe_len(value: Any) -> int:
        return len(value) if isinstance(value, list) else 0

    summary = {
        "stage": stage,
        "prompt_payloads": _safe_len(state.get("prompt_payloads")),
        "raw_outputs": _safe_len(state.get("raw_outputs")),
        "improved_outputs": _safe_len(state.get("improved_outputs")),
        "distractor_validation_passed": _safe_len(state.get("distractor_validation_passed")),
        "distractor_validation_failed": _safe_len(state.get("distractor_validation_failed")),
        "distractor_correction_attempts": state.get("distractor_correction_attempts", 0),
        "quality_validation_passed": _safe_len(state.get("quality_validation_passed")),
        "quality_validation_failed": _safe_len(state.get("quality_validation_failed")),
        "quality_correction_attempts": state.get("quality_correction_attempts", 0),
        "format_fix_attempts": state.get("format_fix_attempts", 0),
        "formatted": _safe_len(state.get("formatted")),
    }
    _append_json_line({"type": "state_summary", **summary})


def _log_formatted_output(state: GraphState) -> None:
    formatted = state.get("formatted", [])
    results = [item.get("result") for item in formatted if isinstance(item, dict)]
    _append_json_line(
        {
            "type": "questions_output",
            "results": results,
        },
        path=_RESULT_QUESTIONS_PATH,
    )


def _reset_run_files() -> None:
    try:
        _STATE_LOG_PATH.write_text("", encoding="utf-8")
        _RESULT_QUESTIONS_PATH.write_text("", encoding="utf-8")
        _FINAL_STATE_PATH.write_text("", encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to reset run files: %s", exc)


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
                if qtype == "MATCHING":
                    correct_count = num_correct
                    incorrect_count = num_incorrect
                    system_prompt = SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
                        "{locale}", locale
                    ).replace("{rubric}", rubric).replace("{bloom_alignment}", bloom_alignment)
                    user_prompt = (
                        USER_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
                            "{difficulty_level}", level
                        )
                        .replace("{source_text}", source_text)
                        .replace("{learning_obj}", lo)
                        .replace("{number_of_questions}", str(number_of_questions))
                        .replace("{num_correct_options}", str(correct_count))
                        .replace("{num_incorrect_options}", str(incorrect_count))
                        .replace("{intermediate_format}", INTERMEDIATE_FORMAT_MATCHING)
                    )
                    response_format = RES_FORMAT_MATCH_COLUMNS
                    intermediate_format = INTERMEDIATE_FORMAT_MATCHING
                else:
                    if qtype == "MULTIPLE_CHOICE_MULTI_SELECT":
                        correct_count = max(1, min(num_correct, 3))
                    else:
                        correct_count = num_correct
                    incorrect_count = num_incorrect
                    response_format = (
                        RES_FORMAT_MULTI_SELECT
                        if qtype == "MULTIPLE_CHOICE_MULTI_SELECT"
                        else RES_FORMAT
                    )
                    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace(
                        "{locale}", locale
                    ).replace("{num_correct_options}", str(correct_count)).replace(
                        "{num_incorrect_options}", str(incorrect_count)
                    ).replace("{rubric}", rubric).replace("{bloom_alignment}", bloom_alignment)
                    user_prompt = (
                        USER_PROMPT_TEMPLATE.replace(
                            "{difficulty_level}", level
                        )
                        .replace("{source_text}", source_text)
                        .replace("{learning_obj}", lo)
                        .replace("{number_of_questions}", str(number_of_questions))
                        .replace("{num_correct_options}", str(correct_count))
                        .replace("{num_incorrect_options}", str(incorrect_count))
                        .replace("{intermediate_format}", INTERMEDIATE_FORMAT_MCQ)
                    )
                    if qtype == "MULTIPLE_CHOICE_MULTI_SELECT":
                        system_prompt = system_prompt.replace(
                            "Ensure exactly the requested number of correct and incorrect options.",
                            "For multi-select, ensure between 1 and 3 correct options and the requested number of incorrect options.",
                        )
                        user_prompt = user_prompt.replace(
                            "Generate exactly {num_correct_options} correct options.",
                            "Generate between 1 and 3 correct options.",
                        )
                    intermediate_format = INTERMEDIATE_FORMAT_MCQ
                payloads.append(
                    {
                        "systemPrompt": system_prompt,
                        "userPrompt": user_prompt,
                        "baseUserPrompt": user_prompt,
                        "responseFormat": response_format,
                        "intermediateFormat": intermediate_format,
                        "learningObjective": lo,
                        "difficultyLevel": level,
                        "questionType": qtype,
                    }
                )

    state["prompt_payloads"] = payloads
    logger.info("Built %s prompt payloads", len(payloads))
    _log_state_summary(state, "build_prompt_payloads")
    return state


def generate_questions(state: GraphState) -> GraphState:
    logger.info("Generating questions with Azure OpenAI")
    client = build_client()
    deployment = get_deployment_name()
    number_of_questions = state["input"].get("numberOfQuestions", 3)
    rubric = state["input"].get("qualityRubric") or DEFAULT_QUALITY_RUBRIC.strip()
    threshold = state["input"].get("qualityThreshold", 85)
    relevancy_threshold = state["input"].get("relevancyThreshold", 85)
    max_attempts = state["input"].get("maxAttempts", 2)
    learning_objectives = _learning_objective_descriptions(state["input"])

    outputs: List[Dict[str, Any]] = []
    for payload in state["prompt_payloads"]:
        attempt = 0
        last_result: Dict[str, Any] = {"error": "No attempts"}
        current_prompt = payload.get("baseUserPrompt") or payload["userPrompt"]
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
                    {"role": "user", "content": current_prompt},
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
            current_prompt = USER_PROMPT_TEMPLATE_CORRECTION.replace(
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
    _log_state_summary(state, "generate_questions")
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
            improved.append({"payload": payload, "result": result})
            continue
        improved.append(_improve_single_output(client, deployment, payload, result))

    state["improved_outputs"] = improved
    logger.info("Improved %s outputs", len(improved))
    _log_state_summary(state, "improve_distractors")
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
        if question_type == "MATCHING":
            if "column_a_answers" not in question or "column_b_answers" not in question:
                return False
            if "answers" not in question and "answer" not in question:
                return False
        else:
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
    _log_state_summary(state, "validate_distractors")
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
    _log_state_summary(state, "correct_distractors")
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
    _log_state_summary(state, "validate_and_fix_format")
    return state


def validate_quality(state: GraphState) -> GraphState:
    logger.info("Validating quality and relevancy")
    client = build_client()
    deployment = get_deployment_name()
    rubric = state["input"].get("qualityRubric") or DEFAULT_QUALITY_RUBRIC.strip()
    threshold = state["input"].get("qualityThreshold", 85)
    relevancy_threshold = state["input"].get("relevancyThreshold", 85)
    learning_objectives = _learning_objective_descriptions(state["input"])

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
    _log_state_summary(state, "validate_quality")
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

    passed_outputs = [
        {"payload": entry["payload"], "result": entry["result"]}
        for entry in state.get("quality_validation_passed", [])
    ]
    state["improved_outputs"] = passed_outputs + corrected_failed
    state["quality_validation_failed"] = []
    state["quality_correction_attempts"] = state.get("quality_correction_attempts", 0) + 1
    _log_state_summary(state, "correct_quality")
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
    _log_state_summary(state, "format_conversion")
    _log_formatted_output(state)
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
    return "end"


def _route_from_format(state: GraphState) -> str:
    format_loop = state.get("format_loop")
    if format_loop is None:
        # Safety guard: if the flag was never set, do not loop endlessly.
        return "end"
    return "validate" if format_loop else "end"


def build_graph():
    graph = StateGraph[GraphState, None, GraphState, GraphState](GraphState)
    graph.add_node("build_prompts", build_prompt_payloads)
    graph.add_node("generate", generate_questions)
    graph.add_node("improve", improve_distractors)
    graph.add_node("validate_distractors", validate_distractors)
    graph.add_node("correct_distractors", correct_distractors)
    graph.add_node("validate_quality", validate_quality)
    graph.add_node("correct_quality", correct_quality)
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
                "quality": [],
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


def _write_final_state(final_state: Dict[str, Any]) -> None:
    try:
        _FINAL_STATE_PATH.write_text(
            json.dumps(final_state, ensure_ascii=True, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Failed to write final state: %s", exc)


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
    _reset_run_files()
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
    final_state = _fill_missing_questions(app, payload, final_state)
    final_state = format_conversion(final_state)
    final_state = validate_and_fix_format(final_state)
    if final_state.get("format_loop"):
        final_state = format_conversion(final_state)
        final_state = validate_and_fix_format(final_state)
    output = _build_output(payload, final_state.get("improved_outputs", []))
    _write_final_state(output)
    return output
