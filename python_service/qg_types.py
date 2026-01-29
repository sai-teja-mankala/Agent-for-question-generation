from typing import Any, Dict, List, Literal, TypedDict

QuestionType = Literal["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT"]


class PipelineInput(TypedDict, total=False):
    locale: str
    sourceText: str
    learningObjectives: List[Any]
    numberOfQuestions: int
    questionsPerSet: int
    questionTypes: List[QuestionType]
    difficultyLevels: List[str]
    numCorrectOptions: int
    numIncorrectOptions: int
    qualityRubric: str
    qualityThreshold: int
    relevancyThreshold: int
    maxAttempts: int
    maxDistractorFixAttempts: int
    maxQualityFixAttempts: int
    maxFormatFixAttempts: int
    assessmentContainerId: str
    internalAssessmentId: str
    learningObjectiveUuid: str
    maxFillAttempts: int


class PromptPayload(TypedDict):
    systemPrompt: str
    userPrompt: str
    baseUserPrompt: str
    responseFormat: str
    intermediateFormat: str
    learningObjective: str
    difficultyLevel: str
    questionType: QuestionType


class GraphState(TypedDict):
    input: PipelineInput
    prompt_payloads: List[PromptPayload]
    scenarios: List[Dict[str, Any]]
    questions: List[Dict[str, Any]]
    raw_outputs: List[Dict[str, Any]]
    improved_outputs: List[Dict[str, Any]]
    formatted: List[Dict[str, Any]]
    distractor_validation_passed: List[Dict[str, Any]]
    distractor_validation_failed: List[Dict[str, Any]]
    distractor_correction_attempts: int
    quality_validation_passed: List[Dict[str, Any]]
    quality_validation_failed: List[Dict[str, Any]]
    quality_correction_attempts: int
    format_fix_attempts: int
    review_distractors_attempts: int
    review_quality_attempts: int
    review_format_attempts: int