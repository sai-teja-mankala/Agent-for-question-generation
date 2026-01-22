from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_pipeline

app = FastAPI()


class PipelineRequest(BaseModel):
    assessmentContainerId: str | None = None
    internalAssessmentId: str | None = None
    locale: str | None = None
    sourceText: str | None = None
    learningObjectives: list[str] | None = None
    learningObjective: list[str] | None = None
    learningObjectiveUuid: str | list[str] | None = None
    numberOfQuestions: int | None = None
    questionTypes: list[str] | None = None
    questionType: list[str] | None = None
    difficultyLevels: list[str] | None = None
    difficultyLevel: str | list[str] | None = None
    numCorrectOptions: int | None = None
    numIncorrectOptions: int | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pipeline/run")
def run(request: PipelineRequest):
    payload = request.model_dump(exclude_none=True)
    if "learningObjectives" not in payload and "learningObjective" in payload:
        payload["learningObjectives"] = payload.pop("learningObjective")
    if "questionTypes" not in payload and "questionType" in payload:
        payload["questionTypes"] = payload.pop("questionType")
    if "difficultyLevels" not in payload and "difficultyLevel" in payload:
        difficulty_level = payload.pop("difficultyLevel")
        payload["difficultyLevels"] = (
            difficulty_level
            if isinstance(difficulty_level, list)
            else [difficulty_level]
        )
    if not payload.get("learningObjectives"):
        raise ValueError("learningObjectives is required and must be a non-empty array")
    if not payload.get("questionTypes"):
        raise ValueError("questionTypes is required and must be a non-empty array")
    if not payload.get("difficultyLevels"):
        raise ValueError("difficultyLevels is required and must be a non-empty array")
    result = run_pipeline(payload)
    return {
        "summary": result.get("summary"),
        "results": result.get("formatted", []),
    }
