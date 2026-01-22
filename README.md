# NestJS Question Generation API

This project is a minimal NestJS API focused on question generation, distractor
checks, quality validation, and conversion to a required format.

## Setup

Install dependencies:

```
npm install
```

## Run

```
npm run start:dev
```

## Azure OpenAI setup

Set these environment variables in `.env` (do not commit secrets):

```
AZURE_OPENAI_ENDPOINT=https://oai-playground-dev-01.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Azure OpenAI chat

`POST /ai/chat`

Body example:

```
{
  "messages": [
    {"role": "developer", "content": "You talk like a pirate."},
    {"role": "user", "content": "Can you help me?"}
  ]
}
```

## Endpoints

### Generate (distractor check + quality)

`POST /questions/generate`

Body example:

```
{
  "topic": "photosynthesis",
  "stem": "What is the main purpose of photosynthesis?",
  "answer": "To convert light energy into chemical energy",
  "distractors": ["To produce heat", "To release carbon dioxide"]
}
```

### Quality check only

`POST /questions/quality`

Body example:

```
{
  "question": {
    "topic": "photosynthesis",
    "stem": "What is the main purpose of photosynthesis?",
    "answer": "To convert light energy into chemical energy",
    "distractors": ["To produce heat", "To release carbon dioxide"],
    "choices": ["..."],
    "difficulty": "medium"
  }
}
```

### Convert to required format

`POST /questions/format`

### Build prompt payloads (system + user + response format)

`POST /questions/prompts`

Body example:

```
{
  "learningObjectives": ["Explain event loop basics"],
  "numberOfQuestions": 3,
  "questionType": "MULTIPLE_CHOICE",
  "perDifficulty": true,
  "difficultyLevel": "Beginner",
  "locale": "en"
}
```

### Build prompt payloads per LO per difficulty (recommended)

`POST /questions/prompts/batch`

Body example:

```
{
  "learningObjectives": [
    "Explain event loop basics",
    "Apply promise chaining in JavaScript"
  ],
  "numberOfQuestions": 3,
  "questionTypes": ["MULTIPLE_CHOICE", "MATCHING"],
  "locale": "en",
  "numCorrectOptions": 1,
  "numIncorrectOptions": 3
}
```

### Convert generated questions to response format

`POST /questions/convert`

Body example:

```
{
  "learningObjective": "Explain event loop basics",
  "levelOfQuiz": "Beginner",
  "questionType": "MULTIPLE_CHOICE",
  "questions": [
    {
      "question": "What does the event loop coordinate?",
      "answers": [
        {"answer": "Async callbacks", "explanation": "It schedules async tasks.", "correct": true},
        {"answer": "GPU rendering", "explanation": "Rendering is handled elsewhere.", "correct": false},
        {"answer": "File system permissions", "explanation": "Permissions are OS-level.", "correct": false},
        {"answer": "CSS parsing", "explanation": "Parsing is done by the engine.", "correct": false}
      ]
    }
  ]
}
```
