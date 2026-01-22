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
Generate questions as per the guidelines and comply with the quality standards provided in the system prompt,
Transcript for question generation: '{source_text}' (Consider this if provided, otherwise ignore)
These questions should strictly adhere to the learning objectives: '{learning_obj}'
Do not alter, rephrase, do not split or infer new learning objectives. Use the given learning objective(s) exactly as they are.
Generate exactly {number_of_questions} questions for each difficulty level (Beginner, Intermediate and Advanced) targeting each of the given learning objective for the given transcript and complying with the quality standards above.
Ensure the response strictly follows this template for quiz generation: {res_format}
"""

USER_PROMPT_PER_DIFFICULTY = """
Generate questions as per the guidelines and comply with the quality standards provided in the system prompt,
Transcript for question generation: '{source_text}' (Consider this if provided, otherwise ignore)
These questions should strictly adhere to the learning objectives: '{learning_obj}'
Do not alter, rephrase, or infer new learning objectives. Use the given learning objective(s) exactly as they are.
Generate exactly {number_of_questions} questions for the '{difficulty_level}' difficulty level targeting each of the given learning objective for the given transcript and complying with the quality standards above.
Ensure the response strictly follows this template for quiz generation: {res_format}
Make sure the 'LevelOfQuiz' value in the output is set to '{difficulty_level}'.
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
Transcript for quiz generation: '{source_text}'
These questions should strictly adhere to the learning objectives: '{learning_obj}'
Do not alter, rephrase, do not split or infer new learning objectives. Use the given learning objective(s) exactly as they are.
Generate exactly {number_of_questions} questions per each difficulty level (Beginner, Intermediate and Advanced) targeting per each learning objective of the given transcript and complying with the quality standards above.
Ensure the response strictly follows this template for quiz generation: {res_format_match_columns}
"""

USER_PROMPT_MATCHING_PER_DIFFICULTY = """
Generate questions as per the guidelines and comply with the quality standards provided in the system prompt.
Transcript for quiz generation: '{source_text}'
These questions should strictly adhere to the learning objectives: '{learning_obj}'
Do not alter, rephrase, or infer new learning objectives. Use the given learning objective(s) exactly as they are.
Generate exactly {number_of_questions} questions for the '{difficulty_level}' difficulty level targeting each of the given learning objective for the given transcript and complying with the quality standards above.
Ensure the response strictly follows this template for quiz generation: {res_format}
Make sure the 'LevelOfQuiz' value in the output is set to '{difficulty_level}'.
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
