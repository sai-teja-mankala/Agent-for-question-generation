import json
import logging
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph

from .llm import build_client, get_deployment_name
from .prompts import (
    RES_FORMAT,
    RES_FORMAT_MATCH_COLUMNS,
    RES_FORMAT_MULTI_SELECT,
    SYSTEM_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS,
    USER_PROMPT_MATCHING_PER_DIFFICULTY,
    USER_PROMPT_PER_DIFFICULTY,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS,
    USER_PROMPT_TEMPLATE_MATCH_COLUMNS,
)
from .types import GraphState, LevelOfQuiz, PipelineInput, PromptPayload, QuestionType

logger = logging.getLogger("pipeline")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")




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
                        .replace("{res_format}", RES_FORMAT_MATCH_COLUMNS)
                    )
                    response_format = RES_FORMAT_MATCH_COLUMNS
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
                        .replace("{res_format}", response_format)
                    )
                payloads.append(
                    {
                        "systemPrompt": system_prompt,
                        "userPrompt": user_prompt,
                        "responseFormat": response_format,
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
    outputs: List[Dict[str, Any]] = []
    for payload in state["prompt_payloads"]:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": payload["systemPrompt"]},
                {"role": "user", "content": payload["userPrompt"]},
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from model", "raw": content}
        outputs.append(
            {
                "payload": payload,
                "result": parsed,
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
        if payload["questionType"] == "MATCHING" or "error" in result:
            improved.append(item)
            continue

        prompt = USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS.replace(
            "{question}", json.dumps(result)
        ).replace("{res_format_multi_select_single_difficulty}", payload["responseFormat"])

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from model", "raw": content}
        improved.append({"payload": payload, "result": parsed})

    state["improved_outputs"] = improved
    logger.info("Improved %s outputs", len(improved))
    return state


def quality_check(state: GraphState) -> GraphState:
    logger.info("Running quality checks")
    quality_results: List[Dict[str, Any]] = []
    for item in state["improved_outputs"]:
        payload = item["payload"]
        result = item["result"]
        if "error" in result:
            quality_results.append({"payload": payload, "quality": {"score": 0, "issues": ["Invalid JSON"]}})
            continue

        issues: List[str] = []
        score = 100
        try:
            questions = result[0]["questions"]
        except Exception:
            questions = []
            score = 0
            issues.append("Result does not match expected format.")

        for question in questions:
            stem = question.get("question", "")
            answers = question.get("answers", [])
            if len(stem) < 15:
                score -= 10
                issues.append("Stem too short.")
            if any(stem.lower() in (a.get("answer", "").lower()) for a in answers):
                score -= 10
                issues.append("Answer text appears in stem.")
            if len(answers) < 4:
                score -= 10
                issues.append("Not enough options.")

        quality_results.append(
            {
                "payload": payload,
                "quality": {
                    "score": max(score, 0),
                    "issues": list(set(issues)),
                    "isPassing": score >= 70,
                },
            }
        )

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
    graph.add_node("quality", quality_check)
    graph.add_node("format", format_conversion)

    graph.set_entry_point("build_prompts")
    graph.add_edge("build_prompts", "generate")
    graph.add_edge("generate", "improve")
    graph.add_edge("improve", "quality")
    graph.add_edge("quality", "format")
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
    final_state["summary"] = {
        "assessmentContainerId": payload.get("assessmentContainerId"),
        "internalAssessmentId": payload.get("internalAssessmentId"),
        "learningObjectiveUuid": payload.get("learningObjectiveUuid"),
        "learningObjectivesCount": len(learning_objectives),
        "numberOfQuestions": number_of_questions,
        "questionTypesCount": len(question_types),
        "difficultyLevelsCount": len(difficulty_levels),
        "expectedTotalQuestions": expected_total,
    }
    return final_state
