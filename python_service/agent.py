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
    USER_PROMPT_TEMPLATE_FIX_FORMAT,
    USER_PROMPT_TEMPLATE_IMPROVE_MATCHING,
    USER_PROMPT_MATCHING_PER_DIFFICULTY,
    USER_PROMPT_PER_DIFFICULTY,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
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
                        USER_PROMPT_MATCHING_PER_DIFFICULTY.replace(
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
                        USER_PROMPT_PER_DIFFICULTY.replace(
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
            payload["userPrompt"] = (
                payload["userPrompt"]
                + "\n\nQuality Rubric:\n"
                + rubric
                + f"\nMinimum score: {threshold}"
                + "\n\nRelevancy must align strictly to these learning objectives:\n"
                + json.dumps(learning_objectives)
                + f"\nMinimum relevancy score: {relevancy_threshold}"
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


def quality_check(state: GraphState) -> GraphState:
    logger.info("Running quality checks")
    quality_results: List[Dict[str, Any]] = []
    for item in state["raw_outputs"]:
        payload = item["payload"]
        quality = item.get("quality", {"score": 0, "issues": ["Not evaluated"], "pass": False})
        relevancy = item.get(
            "relevancy", {"score": 0, "issues": ["Not evaluated"], "pass": False}
        )
        quality_results.append({"payload": payload, "quality": quality, "relevancy": relevancy})

    state["quality"] = quality_results
    logger.info("Quality checks complete for %s outputs", len(quality_results))
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


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("build_prompts", build_prompt_payloads)
    graph.add_node("generate", generate_questions)
    graph.add_node("improve", improve_distractors)
    graph.add_node("validate", validate_and_fix_format)
    graph.add_node("quality", quality_check)
    graph.add_node("format", format_conversion)

    graph.set_entry_point("build_prompts")
    graph.add_edge("build_prompts", "generate")
    graph.add_edge("generate", "quality")
    graph.add_edge("quality", "improve")
    graph.add_edge("improve", "validate")
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
        if isinstance(result, list) and result:
            questions = result[0].get("questions") if isinstance(result[0], dict) else None
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
