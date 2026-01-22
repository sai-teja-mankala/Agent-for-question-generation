# LangGraph Question Generation Service

This project is a Python LangGraph service for sequential question generation:
prompt build → generation → distractor improvement → quality check → formatting.

## Azure OpenAI setup

Set these environment variables in `.env` (do not commit secrets):

```
AZURE_OPENAI_ENDPOINT=https://oai-playground-dev-01.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Setup

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r python_service/requirements.txt
```

### Run (CLI)

```
python python_service/main.py '{"learningObjectives":["Explain event loop basics"],"numberOfQuestions":1,"questionTypes":["MULTIPLE_CHOICE"],"locale":"en"}'
```

### Run (API)

```
uvicorn python_service.api:app --host 0.0.0.0 --port 8000
```

Or:

```
python python_service/server.py
```

Health check:

```
GET http://localhost:8000/health
```

POST `http://localhost:8000/pipeline/run`

```
{
  "learningObjectives": ["Explain event loop basics"],
  "numberOfQuestions": 1,
  "questionTypes": ["MULTIPLE_CHOICE"],
  "locale": "en"
}
```

