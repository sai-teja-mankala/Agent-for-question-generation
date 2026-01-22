RES_FORMAT = """
[
  {
    "LearningObjective": "Learning objective 1",
    "LevelOfQuiz": "Beginner",
    "questions": [
      {
        "question": "What is the capital of France?",
        "answers": [
          {"answer": "Paris", "explanation": "Paris is the capital city of France.", "correct": true},
          {"answer": "London", "explanation": "London is the capital of the UK, not France.", "correct": false},
          {"answer": "Berlin", "explanation": "Berlin is the capital of Germany.", "correct": false},
          {"answer": "Rome", "explanation": "Rome is the capital of Italy.", "correct": false}
        ]
      }
    ]
  }
]
"""

RES_FORMAT_MULTI_SELECT = """
[
  {
    "LearningObjective": "Learning objective 1",
    "LevelOfQuiz": "Beginner",
    "questions": [
      {
        "question": "Which of the following are programming languages?",
        "answers": [
          {"answer": "Python", "explanation": "Python is a popular programming language.", "correct": true},
          {"answer": "Java", "explanation": "Java is widely used for building enterprise applications.", "correct": true},
          {"answer": "HTML", "explanation": "HTML is a markup language, not a programming language.", "correct": false},
          {"answer": "CSS", "explanation": "CSS is used for styling web pages, not for programming logic.", "correct": false},
          {"answer": "Photoshop", "explanation": "Photoshop is an image editing tool, not a programming language.", "correct": false}
        ]
      }
    ]
  }
]
"""

RES_FORMAT_MATCH_COLUMNS = """
[
  {
    "LearningObjective": "Learning objective 1",
    "LevelOfQuiz": "Beginner",
    "questions": [
      {
        "question": "Match each term to its definition.",
        "column_a_answers": [
          {"Option-A": "Project"},
          {"Option-B": "Program"},
          {"Option-C": "Portfolio"},
          {"Option-D": "Some Option"}
        ],
        "column_b_answers": [
          {"Option-1": "A temporary endeavor to create a unique product or result"},
          {"Option-2": "A group of related projects managed in a coordinated way"},
          {"Option-3": "A collection of projects and programs managed together for strategic objectives"},
          {"Option-4": "Enhancing overall customer service"}
        ],
        "answers": [
          {
            "column_b_answers": "A temporary endeavor to create a unique product or result",
            "column_a_answers": "Program",
            "explanation": "This is definition of Program"
          }
        ]
      }
    ]
  }
]
"""

INTERMEDIATE_FORMAT_MCQ = """
{
  "questions": [
    {
      "question": "Question text",
      "answers": [
        {"answer": "Option A", "explanation": "Why it is correct/incorrect", "correct": true},
        {"answer": "Option B", "explanation": "Why it is correct/incorrect", "correct": false}
      ]
    }
  ]
}
"""

INTERMEDIATE_FORMAT_MATCHING = """
{
  "questions": [
    {
      "question": "Match each term to its definition.",
      "column_a_answers": [
        {"Option-A": "Term A"},
        {"Option-B": "Term B"}
      ],
      "column_b_answers": [
        {"Option-1": "Definition 1"},
        {"Option-2": "Definition 2"}
      ],
      "answers": [
        {
          "column_b_answers": "Definition 1",
          "column_a_answers": "Term A",
          "explanation": "Why this is the correct match"
        }
      ]
    }
  ]
}
"""

SYSTEM_PROMPT_TEMPLATE = """
You are a highly knowledgeable AI tasked with generating high-quality, educative, and comprehensive quizzes based on a given course transcript and learning objectives to test how good the learning objectives have been achieved.
Make sure generated quizzes comply with the following quality standards:
- Questions and answers must be very well written with a plain English and perfect grammar.
- Questions should not be too easy, too direct and too specific. They should give the impression that the lecturer thought very well on them. Never ask low-level knowledge questions.
- Questions should be very educative and comprehensive. They should be intermediate or advanced level without being too complicated.
- If the question is about code syntax, include valid code blocks.
- If the course is about coding, generate more coding or syntax related questions.
- Create exactly {num_correct_options} correct answers for each question
- Create exactly {num_incorrect_options} incorrect answers for each question (distractors)
- Make incorrect answers (distractors) appealing and very plausible but definitely incorrect and never NULL.
- Avoid using all of the above and none of the above
- Make sure distractors match the correct answer in terms of length, complexity, phrasing and style
- Ensure that all questions, answers, and distractors are based on the knowledge and information provided in the transcript. Do not introduce new, external information.
- Avoid giving verbal association clues from the question in the correct answer
- Make the choices grammatically consistent with the question.
- Avoid convoluted stems and options
- Avoid overlapping choices
- Minimize repeated text in the choices
- Make questions and answers standalone without giving any reference to the course content.

STRICTLY generate the questions in {locale}.
Response MUST be valid JSON.
"""

USER_PROMPT_TEMPLATE = """
Generate questions as per the guidelines and comply with the quality standards provided in the system prompt.
Transcript for question generation: '{source_text}' (Consider this if provided, otherwise ignore)
Learning objectives: '{learning_obj}'
Generate exactly {number_of_questions} questions for the '{difficulty_level}' difficulty level.
Generate exactly {num_correct_options} correct answers and {num_incorrect_options} incorrect answers (distractors).
Return JSON in this format:
{intermediate_format}
"""

USER_PROMPT_TEMPLATE_CORRECTION = """
You are correcting a single failed question based on evaluation feedback.
Do NOT change the learning objective, difficulty level, or question type.
Only fix the specific failure reasons.
Return ONLY valid JSON in the required response format.

Learning Objective: {learning_obj}
Declared Difficulty: {difficulty_level}
Question Type: {question_type}
Failure Reason(s): {failure_reasons}
Original Question JSON: {question_json}
Required Response Format: {response_format}
"""

SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS = """
You are a highly knowledgeable AI tasked with generating high-quality, educative, and comprehensive quizzes based on a given course transcript and learning objectives to test how good the learning objectives have been achieved.
Make sure generated quizzes comply with the following quality standards:
- Questions and answers must be very well written with a plain English and perfect grammar.
- Questions should not be too easy, too direct and too specific. They should give the impression that the lecturer thought very well on them. Never ask low-level knowledge questions.
- Questions should be very educative and comprehensive.
- If the question is about code syntax, include valid code blocks.
- If the course is about coding, generate more coding or syntax related questions.
- Generate Match the following or Match the columns type questions
- Match the following or Match the columns should have 4 options
- Add explanation for the correct answers
- Avoid giving verbal association clues from the question in the correct answer
- Make the choices gramatically consistent with the question.
- Avoid convoluted stems and options
- Avoid overlapping choices
- Minimize repeated text in the choices
- Make questions and answers standalone without giving any reference to the course content.

STRICTLY generate the questions in {locale}.
Response MUST be valid JSON.
"""

USER_PROMPT_TEMPLATE_MATCH_COLUMNS = """
Generate questions as per the guidelines and comply with the quality standards provided in the system prompt.
Transcript for quiz generation: '{source_text}' (Consider this if provided, otherwise ignore)
Learning objectives: '{learning_obj}'
Generate exactly {number_of_questions} questions for the '{difficulty_level}' difficulty level.
Return JSON in this format:
{intermediate_format}
"""

USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION = """
You are correcting distractors only.
Do NOT change the question stem or the correct answer.
Keep the number of options unchanged.
Improve ONLY the distractors on answer options based on these criteria:
- Plausibility
- Construct Relevance
- Distinctiveness
- Incorrectness Clarity
- Misconception Representation

Failure Reason(s): {failure_reasons}
Question JSON: {question_json}
Required Response Format: {response_format}
"""

SYSTEM_PROMPT_TEMPLATE_BLOOM_ALIGNMENT = """
You are a strict assessment evaluator responsible for verifying
whether a question’s cognitive demand correctly matches its declared
DIFFICULTY level using Bloom’s Taxonomy.

You must evaluate ONLY cognitive alignment.
You do NOT rewrite the question.
You do NOT suggest improvements.
You ONLY determine correctness or failure.
"""

USER_PROMPT_TEMPLATE_BLOOM_ALIGNMENT = """
Declared Difficulty Level: {difficulty_level}
Question: {question}
Options (if applicable): {options}
Correct Answer: {correct_answer}
Learning Objective: {learning_objective}

AUTHORITATIVE DIFFICULTY ↔ BLOOM’S MAPPING (MANDATORY)

EASY: KNOWLEDGE, UNDERSTAND
INTERMEDIATE: APPLY, ANALYZE
DIFFICULT: EVALUATE, CREATE

Disallowed:
- EASY: APPLY/ANALYZE/EVALUATE/CREATE
- INTERMEDIATE: KNOWLEDGE/UNDERSTAND/EVALUATE/CREATE
- DIFFICULT: KNOWLEDGE/UNDERSTAND/APPLY/ANALYZE

EVALUATION RULES (STRICT)
1) Determine the lowest Bloom’s level required to answer correctly.
2) Compare to allowed levels for the declared difficulty.
3) Below or above allowed range → FAIL.
4) Any ambiguity → FAIL.

AUTOMATIC FAILURE CONDITIONS
- Cognitive demand is unclear or mixed
- Question wording allows multiple cognitive interpretations
- Learning objective conflicts with detected Bloom’s level

OUTPUT FORMAT (STRICT JSON ONLY)
{
  "verdict": "PASS" | "FAIL",
  "declaredDifficulty": "EASY | INTERMEDIATE | DIFFICULT",
  "detectedBloomLevel": "KNOWLEDGE | UNDERSTAND | APPLY | ANALYZE | EVALUATE | CREATE",
  "difficultyAlignment": true | false,
  "failureReason": "<explicit Bloom–difficulty mismatch if FAIL, otherwise null>"
}
"""

SYSTEM_PROMPT_TEMPLATE_DISTRACTOR_QUALITY = """
You are a strict distractor evaluator. Assess EACH distractor individually.
You must evaluate ONLY the distractor quality metrics below.
Do NOT rewrite distractors. Do NOT suggest improvements.
"""

USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY = """
Question: {question}
Correct Answer: {correct_answer}
Distractors: {distractors}
Learning Objective: {learning_objective}
Skill/Construct: {skill_or_construct}

METRICS (score each 1–5)
1) Plausibility
- How realistic the distractor sounds as something a well-meaning leader might do/say.
- High score = tempting to unsure learners.

2) Construct Relevance
- How directly the distractor relates to the specific skill/construct being assessed.
- High score = wrong application of the target skill (not irrelevant or off-topic).

3) Distinctiveness
- How clearly it differs from correct answer AND other options in idea/approach.
- High score = different type of mistake, not a near-duplicate.

4) Incorrectness Clarity
- How clearly the option is wrong in realistic leadership context.
- High score = clearly wrong, not debatable or “it depends.”

5) Misconception Representation
- Whether it reflects a common misconception/error pattern.
- High score = maps to recognizable misunderstanding.

STRICT SCORING RULES
- Use integers 1–5 only.
- If any metric is ambiguous, score 2 or lower.
- If distractor could be reasonably correct, Incorrectness Clarity must be ≤2.

OUTPUT FORMAT (STRICT JSON ONLY)
{
  "verdict": "PASS" | "FAIL",
  "overallNotes": "<short, objective summary>",
  "distractors": [
    {
      "text": "<distractor>",
      "scores": {
        "plausibility": 1-5,
        "constructRelevance": 1-5,
        "distinctiveness": 1-5,
        "incorrectnessClarity": 1-5,
        "misconceptionRepresentation": 1-5
      },
      "pass": true | false,
      "failReason": "<why it failed, else null>"
    }
  ],
  "thresholds": {
    "minAverageScore": 3.5,
    "minPerMetricScore": 3
  }
}

PASS/FAIL LOGIC
- A distractor passes if ALL metrics >= minPerMetricScore AND average >= minAverageScore.
- Overall verdict is PASS only if ALL distractors pass.
"""

SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS = """
You are an expert assessment and item-writing specialist. Your task is to REVIEW and REWRITE the distractors (incorrect options) of a multiple-choice question to ensure they test critical thinking and strategic judgment rather than simple recall.
Your Core Objectives:
    1. Reveal Gaps in Strategic Thinking: Distractors should not be "factually false" in a vacuum; they should be suboptimal choices that a learner might make if they lack nuance or focus on the wrong priority.
    2. Eliminate "Easy" Recall: If a distractor can be eliminated simply because it is a "bad" or "incorrect" fact, it is too weak.
    3. Plausible Competitors: Ensure distractors represent "near-miss" decisions—actions that are technically correct in other contexts but incorrect for this specific scenario.
    4. Preserve the original intent, topic, and difficulty band of the item.
OUTPUT REQUIREMENTS:
    - Only return the improved question in EXACTLY the format specified in the user prompt (including labels, ordering, and any metadata placeholders).
    - Do not add, remove, or reorder answer choices.
    - Do not add any commentary, explanation, or markdown.
    - If no changes are needed, return the question exactly as received, preserving formatting.
"""

USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS = """
Validate the following question:

Question with answer choices : {question}
Response format: {res_format_multi_select_single_difficulty}
"""

SYSTEM_PROMPT_TEMPLATE_IMPROVE_MATCHING = """
You are an expert assessment designer. Improve match-the-columns questions by adding or refining distractor options.
Rules:
- Keep the original question intent and correct matches.
- Ensure exactly 4 options in column A and 4 options in column B.
- Add plausible distractors if options are missing or too obvious.
- Do not change the meaning of correct answers.
- Return ONLY valid JSON in the exact response format.
"""

USER_PROMPT_TEMPLATE_IMPROVE_MATCHING = """
Improve the following matching question. Add or refine distractor options if needed.

Question: {question}
Response format: {res_format_match_columns}
"""

SYSTEM_PROMPT_TEMPLATE_FIX_FORMAT = """
You are a strict JSON formatter. Convert the given content into the required response format.
Rules:
- Output ONLY valid JSON.
- Match the provided response format exactly.
- Preserve the original meaning and answers.
"""

USER_PROMPT_TEMPLATE_FIX_FORMAT = """
Required response format: {res_format}

Input to transform:
{raw_output}
"""

SYSTEM_PROMPT_TEMPLATE_QUALITY_CHECK = """
You are a strict rubric-based evaluator for assessment items.
Return ONLY JSON with this schema:
{
  "score": 0-100,
  "issues": ["..."],
  "pass": true/false
}
Use the rubric and evaluate the provided questions.
"""

USER_PROMPT_TEMPLATE_QUALITY_CHECK = """
Quality Rubric:
{rubric}

Questions JSON:
{questions}

Pass threshold: {threshold}
"""

SYSTEM_PROMPT_TEMPLATE_RELEVANCY_CHECK = """
You are a strict evaluator for relevance of questions to learning objectives.
Return ONLY JSON with this schema:
{
  "score": 0-100,
  "issues": ["..."],
  "pass": true/false
}
Evaluate relevance to the provided learning objectives.
"""

USER_PROMPT_TEMPLATE_RELEVANCY_CHECK = """
Learning Objectives:
{learning_objectives}

Questions JSON:
{questions}

Pass threshold: {threshold}
"""
