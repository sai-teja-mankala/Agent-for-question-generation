from typing import Any, Dict, List, Literal, TypedDict

QuestionType = Literal["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT", "MATCHING"]
LevelOfQuiz = Literal["Beginner", "Intermediate", "Advanced"]


class PipelineInput(TypedDict, total=False):
    locale: str
    sourceText: str
    learningObjectives: List[str]
    numberOfQuestions: int
    questionTypes: List[QuestionType]
    difficultyLevels: List[LevelOfQuiz]
    numCorrectOptions: int
    numIncorrectOptions: int
    qualityRubric: str
    qualityThreshold: int
    relevancyRubric: str
    relevancyThreshold: int
    maxAttempts: int
    assessmentContainerId: str
    internalAssessmentId: str
    learningObjectiveUuid: str


class PromptPayload(TypedDict):
    systemPrompt: str
    userPrompt: str
    responseFormat: str
    intermediateFormat: str
    learningObjective: str
    difficultyLevel: LevelOfQuiz
    questionType: QuestionType


class GraphState(TypedDict):
    input: PipelineInput
    prompt_payloads: List[PromptPayload]
    raw_outputs: List[Dict[str, Any]]
    improved_outputs: List[Dict[str, Any]]
    quality: List[Dict[str, Any]]
    formatted: List[Dict[str, Any]]
    distractor_validation_passed: List[Dict[str, Any]]
    distractor_validation_failed: List[Dict[str, Any]]
    distractor_correction_attempts: int
    quality_validation_passed: List[Dict[str, Any]]
    quality_validation_failed: List[Dict[str, Any]]
    quality_correction_attempts: int
