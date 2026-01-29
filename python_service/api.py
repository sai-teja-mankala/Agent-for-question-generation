from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_pipeline

app = FastAPI()


class LearningObjectiveItem(BaseModel):
    id: str | None = None
    description: str | None = None


class PipelineRequest(BaseModel):
    assessmentContainerId: str | None = None
    internalAssessmentId: str | None = None
    locale: str | None = None
    sourceText: str | None = None
    learningObjectives: list[str | LearningObjectiveItem] | None = None
    learningObjective: list[str] | None = None
    learningObjectiveUuid: str | list[str] | None = None
    numberOfQuestions: int | None = None
    questionTypes: list[str] | None = None
    questionType: list[str] | None = None
    difficultyLevels: list[str] | None = None
    difficultyLevel: str | list[str] | None = None
    numCorrectOptions: int | None = None
    numIncorrectOptions: int | None = None
    qualityRubric: str | None = None
    qualityThreshold: int | None = None
    relevancyThreshold: int | None = None
    maxAttempts: int | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pipeline/run")
def run(request: PipelineRequest):
    import json
    from datetime import datetime
    from pathlib import Path
    
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
    
    # Save formatted result to file
    try:
        result_file = Path(f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with result_file.open("w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save result file: {e}")
    
    return result
