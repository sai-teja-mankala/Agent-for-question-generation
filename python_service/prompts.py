# ==========================================
# DECOMPOSED GENERATION PROMPTS (v1 Enhanced)
# ==========================================

SYSTEM_CONTRACT = """
You are an expert assessment designer specialized in creating high-quality, discriminating assessment items.

CRITICAL QUALITY STANDARDS:
1. ALIGNMENT: Every question must directly test the learning objective - no tangential concepts.
2. COGNITIVE DEMAND: Match Bloom's level precisely (see mapping below).
3. PLAUSIBILITY: All distractors must be tempting to someone with partial knowledge.
4. DISTINCTIVENESS: Each distractor represents a DIFFERENT misconception or error pattern.
5. NO TRIVIAL REJECTIONS: Avoid obviously wrong, extreme, or "straw man" options.
6. REALISTIC CONTEXT: Use workplace scenarios that professionals actually face.
7. PRECISION: Be specific, avoid vague or generic wording.

FORBIDDEN PATTERNS (will cause immediate failure):
- "All of the above" or "None of the above"
- Extreme behaviors: "ignore all feedback", "never listen", "always criticize"
- Obviously wrong facts that can be eliminated without understanding
- Generic advice disconnected from the specific learning objective
- Distractors that are near-duplicates of each other
- Questions that test general knowledge instead of the specific skill

DIFFICULTY MAPPING (STRICT):
- Easy: Recognize, recall, define, or explain core concepts. Direct questions. No application or decision-making.
  Example: "What is X?" "Which describes Y?" "What are the key elements of Z?"
- Intermediate: Apply the skill in routine professional situations. Choose among standard approaches.
  Example: "How should a manager apply X when Y?" "What step should be taken to Z?"
- Advanced: Analyze competing priorities, evaluate trade-offs, design strategies under constraints.
  Example: "How should a leader evaluate X given constraints Y and Z?" "What factors must be balanced when..."

OUTPUT: Return ONLY valid JSON. No markdown blocks. No explanatory text.
"""

SCENARIO_GENERATION_PROMPT = """
Generate a set of of 10 may be important points that user can have assessment so that we can generate hight quality questions around that specifi topic of the LO

REQUIREMENTS:
- Generic Level Definitions (to adapt):
Level 1: Recognizes the concept, recalls basic facts, but cannot apply. (Bloom: Remembering)
Level 2: Understands fundamentals, applies in simple contexts. (Bloom: Understanding)
Level 3: Applies skill independently in standard situations. (Bloom: Applying)
Level 4: Analyzes, adapts, and integrates skill across contexts. (Bloom: Analyzing)
Level 5: Mastery; evaluates, innovates, and sets best practices. (Bloom: Evaluating & Creating)

Generic Level Definitions (to Adapt):
Level 1
Skill Complexity: Very basic; recognizes the concept but cannot perform it.
Skill Knowledge: Possesses surface-level familiarity; can recall facts, terms, or definitions.
Bloom's Taxonomy Alignment: Remembering (recognize, list, recall).
Definition: Individuals know that the skill exists, understand its basic purpose, and can identify when it is relevant, but they do not yet apply it.

Level 2
Skill Complexity: Simple, structured tasks with predictable outcomes.
Skill Knowledge: Understands basic principles and simple processes; limited breadth.
Bloom's Taxonomy Alignment: Understanding (explain, summarize, classify).
Definition: Individuals can describe the fundamentals of the skill and apply it in straightforward, guided situations but lack adaptability in unfamiliar contexts.

Level 3
Skill Complexity: Moderate; applies the skill to standard problems and varying contexts.
Skill Knowledge: Demonstrates working knowledge of methods, tools, and practices.
Bloom's Taxonomy Alignment: Applying (execute, implement, use).
Definition: Individuals apply the skill independently in routine tasks, make appropriate choices among standard methods, and achieve consistent results.

Level 4
Skill Complexity: Advanced; handles complexity and interdependencies within the skill.
Skill Knowledge: Strong understanding of concepts, techniques, and multiple approaches.
Bloom's Taxonomy Alignment: Analyzing (differentiate, compare, organize).
Definition: Individuals can analyze situations, adapt the skill to diverse scenarios, and integrate it with other knowledge areas to solve complex problems.

Level 5
Skill Complexity: Expert-level; applies the skill to novel, complex, and strategic contexts.
Skill Knowledge: Deep mastery, including principles, cross-domain integration, and innovation.
Bloom's Taxonomy Alignment: Evaluating & Creating (design, innovate, justify, set standards).
Definition: Individuals demonstrate mastery by critically evaluating, designing, and innovating within the skill area. They extend its application to new domains and establish best practices.

Canonical Mapping (authoritative):
- Easy: Level 1, Level 2
- Intermediate: Level 3, level 4
- Advanced: Level 4, Level 5

Return JSON: {"scenario": "...", "decisionPoint": "..."}
"""

QUESTION_GENERATION_PROMPT = """
Write ONE question that directly tests the learning objective at the specified difficulty level.

DIFFICULTY-SPECIFIC REQUIREMENTS:

Easy (Recall/Recognition):
- Ask for definitions, key elements, or identification
- Use clear, direct language: "What is...", "Which describes...", "What are the key elements of..."
- Focus on foundational knowledge required before application
- Question should be answerable with basic understanding

Intermediate (Application):
- Present a routine professional situation
- Ask how to apply the skill in standard contexts
- Use: "How should X apply...", "What step should Y take...", "Which approach..."
- Require choosing among established practices
- If scenario provided, reference it directly

Advanced (Analysis/Evaluation):
- Use the scenario's complexity (constraints, competing priorities)
- Ask for strategic judgment: "How should X evaluate...", "What factors must Y balance..."
- Require analysis of trade-offs, not just selecting "best practice"
- The question stem should acknowledge the complexity

QUALITY STANDARDS:
✓ Grammatically perfect and professionally worded
✓ Directly tied to the learning objective
✓ Clear, unambiguous phrasing
✓ Appropriate length (not overly verbose or terse)
✗ Vague language: "properly", "effectively" without context
✗ Leading questions that telegraph the answer

If failure_reasons provided: Completely rewrite to avoid those specific issues. Do not reuse similar wording.

Return JSON: {"questionText": "..."}
"""

OPTIONS_GENERATION_PROMPT = """
Create answer options that discriminate between learners who truly understand the skill and those with partial or flawed knowledge.

CORRECT OPTION(S):
✓ Clearly best answer given the context
✓ Specific and actionable (not generic advice)
✓ Directly addresses the question's core requirement
✓ Concise: 10-20 words (similar length to distractors)
✓ Professional tone
✗ Overly comprehensive "golden answer" that's obviously longest
✗ Using words from the question stem verbatim
✗ So perfect it sounds unrealistic

INCORRECT OPTIONS (DISTRACTORS) - CRITICAL TAXONOMY:

MANDATORY: Each of your 3 distractors MUST come from a DIFFERENT category below.
Do NOT create two distractors from the same category.

**CATEGORY 1: SCOPE/BOUNDARY ERROR**
- Addresses wrong aspect of the skill (e.g., focuses on communication when question is about planning)
- Confuses the skill with a related but different skill
- Applies the skill in wrong domain/context
Example: Question about "creating vision" → Distractor focuses on "implementing tactics"

**CATEGORY 2: TIMING/SEQUENCE ERROR**  
- Wrong order of steps
- Acts too early or too late in the process
- Skips necessary prerequisites
- Prioritizes incorrectly (short-term vs long-term)
Example: Question about "strategic planning" → Distractor focuses on "immediate execution"

**CATEGORY 3: STAKEHOLDER/FOCUS ERROR**
- Focuses on wrong stakeholder group (individual vs team vs organization)
- Misidentifies whose needs to prioritize
- Wrong level of analysis (micro vs macro)
Example: Question about "team vision" → Distractor focuses on "individual goals"

**CATEGORY 4: METHOD/APPROACH ERROR**
- Correct goal but wrong method to achieve it
- Uses outdated/inappropriate technique
- Over-relies on one tool when integration needed
- Correct in other contexts but wrong here
Example: Question about "communicating vision" → Distractor relies only on "written documents"

**CATEGORY 5: COMPLETENESS ERROR**
- Partially correct but missing critical element
- Addresses one dimension while ignoring others
- Correct understanding but incomplete application
Example: Question about "vision alignment" → Distractor only addresses "clarity" but not "buy-in"

**CATEGORY 6: CONSTRAINT/TRADE-OFF ERROR** (Advanced questions only)
- Ignores stated constraints (budget, time, resources)
- Fails to balance competing priorities
- Optimizes one factor at expense of critical others
Example: Question with safety + efficiency constraints → Distractor sacrifices safety for efficiency

CREATION PROCESS:
1. Read the question and identify the CORE SKILL being tested
2. Select 3 DIFFERENT categories from above (for 3 distractors)
3. For EACH category, create ONE distractor that represents that specific error type
4. Ensure each distractor is plausible to someone with 60-70% understanding
5. Make all options similar in length (±3 words) and professional tone

QUALITY REQUIREMENTS:
✓ Each distractor from DIFFERENT category above
✓ PLAUSIBLE to someone with partial knowledge
✓ Each sounds reasonable on first read
✓ Similar length (±3 words from correct option)
✓ Similar grammatical structure
✓ Specific and concrete (not vague generalities)
✗ Obviously wrong, extreme, or absurd: "never listen", "ignore all", "always criticize"
✗ Factually incorrect in any context (easy to eliminate)
✗ Generic advice unrelated to the specific skill
✗ Two distractors from the same category above
✗ Implausible behaviors professionals would never consider

EXPLANATIONS (15-25 words each):
- For correct: Why this is best in this context
- For incorrect: What misconception it represents (cite the category)

SELF-CHECK before submitting:
1. Did I use 3 DIFFERENT categories from the taxonomy?
2. Is each distractor plausible to someone with partial knowledge?
3. Are all options similar in length and structure?
4. Would a professional with 60-70% understanding find them all reasonable?

Return JSON: {"answers":[{"answerText":"...","isCorrect":true/false,"explanation":"..."}]}
"""

OPTIONS_CORRECTION_PROMPT = """
Rewrite ONLY the incorrect options to address the failure reasons below.
Keep the question and correct option unchanged.
Each rewritten distractor must:
- Address the specific failure reason
- Be plausible and represent a distinct misconception
- Match the correct option in length and tone
- Not be obviously wrong or extreme

Return JSON in the same format: {"answers":[{"answerText":"...","isCorrect":true/false,"explanation":"..."}]}.
"""

# ==========================================
# ORIGINAL v1 FORMATS
# ==========================================

RES_FORMAT = """
[
  {
    "LearningObjective": "Learning objective 1",
    "questions": [
      {
        "questionText": "What is the capital of France?",
        "answer": [
          {"answerText": "Paris", "explanation": "Paris is the capital city of France.", "isCorrect": true},
          {"answerText": "London", "explanation": "London is the capital of the UK, not France.", "isCorrect": false},
          {"answerText": "Berlin", "explanation": "Berlin is the capital of Germany.", "isCorrect": false},
          {"answerText": "Rome", "explanation": "Rome is the capital of Italy.", "isCorrect": false}
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
    "questions": [
      {
        "questionText": "Which of the following are programming languages?",
        "answer": [
          {"answerText": "Python", "explanation": "Python is a popular programming language.", "isCorrect": true},
          {"answerText": "Java", "explanation": "Java is widely used for building enterprise applications.", "isCorrect": true},
          {"answerText": "HTML", "explanation": "HTML is a markup language, not a programming language.", "isCorrect": false},
          {"answerText": "CSS", "explanation": "CSS is used for styling web pages, not for programming logic.", "isCorrect": false},
          {"answerText": "Photoshop", "explanation": "Photoshop is an image editing tool, not a programming language.", "isCorrect": false}
        ]
      }
    ]
  }
]
"""

# ==========================================
# UNUSED - MATCHING QUESTION TYPE (REMOVED)
# ==========================================

# RES_FORMAT_MATCH_COLUMNS = """
# [
#   {
#     "LearningObjective": "Learning objective 1",
#     "questions": [
#       {
#         "questionText": "Match each term to its definition.",
#         "column_a_answers": [
#           {"Option-A": "Project"},
#           {"Option-B": "Program"},
#           {"Option-C": "Portfolio"},
#           {"Option-D": "Some Option"}
#         ],
#         "column_b_answers": [
#           {"Option-1": "A temporary endeavor to create a unique product or result"},
#           {"Option-2": "A group of related projects managed in a coordinated way"},
#           {"Option-3": "A collection of projects and programs managed together for strategic objectives"},
#           {"Option-4": "Enhancing overall customer service"}
#         ],
#         "answers": [
#           {
#             "column_b_answers": "A temporary endeavor to create a unique product or result",
#             "column_a_answers": "Program",
#             "explanation": "This is definition of Program"
#           }
#         ]
#       }
#     ]
#   }
# ]
# """

DEFAULT_QUALITY_RUBRIC = """
Quality Rubric for MCQ/Matching Items (0–100)

1) Learning Objective Alignment (0–20)
- 0–5: Question is off-topic or only loosely related.
- 6–12: Partially aligned; tests a related concept but not the LO.
- 13–20: Directly and clearly measures the LO.

2) Cognitive Level Alignment (Bloom vs Difficulty) (0–20)
- 0–5: Bloom level clearly mismatched to declared difficulty.
- 6–12: Partially aligned; ambiguous cognitive demand.
- 13–20: Clear and correct Bloom alignment.

3) Question Clarity & Precision (0–15)
- 0–5: Ambiguous, vague, or poorly worded.
- 6–10: Mostly clear but still some ambiguity.
- 11–15: Clear, precise, and unambiguous.

4) Distractor Quality (0–20)
- 0–5: Implausible or irrelevant distractors.
- 6–12: Mixed quality; some weak or too obvious.
- 13–20: Plausible, distinct, and misconception-based.

5) Answer Key Validity (0–10)
- 0–3: Correct answer unclear or multiple correct options.
- 4–7: Mostly valid but potentially arguable.
- 8–10: Single, clearly correct answer.

6) Non-redundancy & Balance (0–10)
- 0–3: Repetitive, overlapping options or stems.
- 4–7: Minor redundancy.
- 8–10: Balanced, non-overlapping options.

7) Language & Tone (0–5)
- 0–2: Poor grammar, awkward phrasing.
- 3–4: Mostly correct with minor issues.
- 5: Professional, polished language.

Scoring guidance:
- >=85 = PASS
- 70-84 = Needs minor improvement
- <70 = FAIL
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

BLOOM_ALIGNMENT_GENERATION_GUIDANCE = """
Generic Level Definitions (to adapt):
Level 1: Recognizes the concept, recalls basic facts, but cannot apply. (Bloom: Remembering)
Level 2: Understands fundamentals, applies in simple contexts. (Bloom: Understanding)
Level 3: Applies skill independently in standard situations. (Bloom: Applying)
Level 4: Analyzes, adapts, and integrates skill across contexts. (Bloom: Analyzing)
Level 5: Mastery; evaluates, innovates, and sets best practices. (Bloom: Evaluating & Creating)

Generic Level Definitions (Explained):
Level 1
Skill Complexity: Very basic; recognizes the concept but cannot perform it.
Skill Knowledge: Possesses surface-level familiarity; can recall facts, terms, or definitions.
Bloom's Taxonomy Alignment: Remembering (recognize, list, recall).
Definition: Individuals know that the skill exists, understand its basic purpose, and can identify when it is relevant, but they do not yet apply it.

Level 2
Skill Complexity: Simple, structured tasks with predictable outcomes.
Skill Knowledge: Understands basic principles and simple processes; limited breadth.
Bloom's Taxonomy Alignment: Understanding (explain, summarize, classify).
Definition: Individuals can describe the fundamentals of the skill and apply it in straightforward, guided situations but lack adaptability in unfamiliar contexts.

Level 3
Skill Complexity: Moderate; applies the skill to standard problems and varying contexts.
Skill Knowledge: Demonstrates working knowledge of methods, tools, and practices.
Bloom's Taxonomy Alignment: Applying (execute, implement, use).
Definition: Individuals apply the skill independently in routine tasks, make appropriate choices among standard methods, and achieve consistent results.

Level 4
Skill Complexity: Advanced; handles complexity and interdependencies within the skill.
Skill Knowledge: Strong understanding of concepts, techniques, and multiple approaches.
Bloom's Taxonomy Alignment: Analyzing (differentiate, compare, organize).
Definition: Individuals can analyze situations, adapt the skill to diverse scenarios, and integrate it with other knowledge areas to solve complex problems.

Level 5
Skill Complexity: Expert-level; applies the skill to novel, complex, and strategic contexts.
Skill Knowledge: Deep mastery, including principles, cross-domain integration, and innovation.
Bloom's Taxonomy Alignment: Evaluating & Creating (design, innovate, justify, set standards).
Definition: Individuals demonstrate mastery by critically evaluating, designing, and innovating within the skill area. They extend its application to new domains and establish best practices.

Canonical Mapping (authoritative):
- Easy: Level 1, Level 2
- Intermediate: Level 3
- Advanced: Level 4, Level 5
"""

# ==========================================
# UNUSED - OLD MONOLITHIC GENERATION PROMPTS
# (Replaced by decomposed prompts above)
# ==========================================

# SYSTEM_PROMPT_TEMPLATE = """
# You are an expert assessment designer and psychometrician.

# Your task is to generate high-quality quiz questions that accurately measure whether the given Learning Objective has been achieved.

# STRICT RULES:
# - The declared difficulty level MUST strictly match the Bloom level defined below.
# - Do NOT generate questions below or above the allowed Bloom level.
# - Do NOT mix Bloom levels within a single question.
# - NEVER generate opinion-based or generic questions.
# - NEVER ask trivial or overly broad questions.

# **DIFFICULTY ↔ BLOOM MAPPING (MANDATORY):**
# {bloom_alignment}

# **IMPORTANT: Difficulty-to-Cognition Mapping (MANDATORY):**

# Easy questions MUST align ONLY with:
# - Level 1 (Recognizes, recalls, identifies concepts; no application)
# - Level 2 (Explains, summarizes, classifies; applies only in simple, guided contexts)

# Intermediate questions MUST align ONLY with:
# - Level 3 (Applies the skill independently in standard, routine situations)

# Advanced questions MUST align ONLY with:
# - Level 4 (Analyzes, adapts, integrates across contexts)
# - Level 5 (Evaluates, designs, innovates, sets best practices)

# Hard constraints:
# - Do NOT generate application, analysis, evaluation, or judgment questions for Easy.
# - Do NOT generate recall-only or definition-only questions for Intermediate.
# - Do NOT generate opinion-only or generic explanation questions for Advanced.

# Difficulty-to-Cognition Mapping (MANDATORY):

# Easy questions MUST align ONLY with:
# - Level 1 (Recognizes, recalls, identifies concepts; no application)
# - Level 2 (Explains, summarizes, classifies; applies only in simple, guided contexts)

# Intermediate questions MUST align ONLY with:
# - Level 3 (Applies the skill independently in standard, routine situations)

# Advanced questions MUST align ONLY with:
# - Level 4 (Analyzes, adapts, integrates across contexts)
# - Level 5 (Evaluates, designs, innovates, sets best practices)

# Hard constraints:
# - Do NOT generate application, analysis, evaluation, or judgment questions for Easy.
# - Do NOT generate recall-only or definition-only questions for Intermediate.
# - Do NOT generate opinion-only or generic explanation questions for Advanced.

# CONTENT RULES:
# - Use clear, professional English.
# - Avoid vague wording and subjective phrasing.
# - Avoid “all of the above / none of the above”.
# - Ensure distractors are plausible and aligned to the same construct.
# - Ensure options are parallel in structure and similar in length/tone.
# - Avoid giveaway options that are obviously wrong or easy to eliminate.
# - Ensure exactly the requested number of correct and incorrect options.
# - Do NOT introduce information not present in the provided transcript (if any).

# STRUCTURAL CONSTRAINTS (HIGH LEVEL ONLY):
# - MCQ: 4 options, exactly 1 correct
# - MCQ Multi-select: 4 options, 1–3 correct
# - Matching: 4 items per column, 4 correct mappings

# QUALITY BAR:
# - Questions must be realistic, educative, and discriminating.
# - A learner who does not understand the concept should plausibly choose a distractor.
# - If quality cues are not explicit, choose options that would be defensible to a partially competent learner and are not obvious eliminations.
# - For Advanced, include at least one Level 5 (Evaluate/Create) question per learning objective when multiple questions are requested.

# Quality Rubric (use this as strict measurement during generation):
# {rubric}

# Output requirements:
# - Do NOT worry about final JSON formatting but it should be valid JSON.
# - A later system will convert your output into the required schema.
# - Focus ONLY on cognitive quality, Bloom alignment, and learning objective alignment.
# - Before returning, validate that all rules are satisfied and revise if any rule is violated.
# """

# USER_PROMPT_TEMPLATE = """
# Generate assessment questions following the system rules.
#
# Learning Objective:
# {learning_obj}
#
# Difficulty Level:
# {difficulty_level}
#
# Transcript (use only if provided):
# {source_text}
#
# Requirements:
# - Generate exactly {number_of_questions} questions.
# - Each question must strictly match the declared difficulty.
# - Generate exactly {num_correct_options} correct options.
# - Generate exactly {num_incorrect_options} incorrect but plausible distractors.
#
# Do NOT worry about final JSON formatting.
# A later system will convert your output into the required schema.
# Focus ONLY on:
# - cognitive quality
# - Bloom alignment
# - learning objective alignment
# """

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


USER_PROMPT_TEMPLATE_DISTRACTOR_CORRECTION = """
You are correcting distractors only.
Do NOT change the question stem or the correct answer.
Keep the number of options unchanged.
Use the failure reasons to rewrite ONLY the distractors so they meet the required criteria:
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
You are a strict assessment evaluator.

Your only task is to verify whether the cognitive demand of the question
correctly matches the declared difficulty level using Bloom’s Taxonomy.

Rules:
1. Determine the LOWEST Bloom level required to answer correctly.
2. Compare it to the allowed Bloom levels for the declared difficulty.
3. If outside the allowed range → FAIL.
4. If Bloom level is ambiguous → FAIL.
5. If question wording allows multiple Bloom interpretations → FAIL.

You do NOT rewrite.
You do NOT suggest improvements.
You ONLY evaluate alignment.

Return STRICT JSON only.
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
METRICS (score each 1–5)
1) Plausibility
- How realistic the distractor sounds as a choice a partially informed learner might choose.
- High score = tempting to unsure learners.

2) Construct Relevance
- How directly the distractor relates to the specific skill/construct being assessed.
- High score = wrong application of the target skill (not irrelevant or off-topic).

3) Distinctiveness
- How clearly it differs from correct answer AND other options in idea/approach.
- High score = different type of mistake, not a near-duplicate, but still plausible enough to be tempting.

4) Incorrectness Clarity
- How clearly the option is wrong in the given context.
- High score = clearly wrong, not debatable or “it depends.”

5) Misconception Representation
- Whether it reflects a common misconception/error pattern.
- High score = maps to recognizable misunderstanding.

6) Non-obviousness
- Whether the distractor avoids being obviously wrong, jokey, off-topic, or extreme.
- High score = not easily eliminated by test-taking cues.

7) Parallelism & Length Parity
- Whether the distractor matches the correct option in length, tone, and formality.
- High score = similar structure and specificity, no giveaway wording.

Distinctiveness enforcement:
- Each distractor must map to a different misconception bucket.
- If two distractors share the same misconception bucket, mark those distractors as FAIL and mention the shared bucket in failReason.

STRICT SCORING RULES
- Use integers 1–5 only.
- If any metric is ambiguous, score 2 or lower.
- If distractor could be reasonably correct, Incorrectness Clarity must be ≤2.
- If a distractor is obviously wrong, score Non-obviousness ≤2.
- If distractor length/tone is mismatched, score Parallelism & Length Parity ≤2.

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
        "misconceptionRepresentation": 1-5,
        "nonObviousness": 1-5,
        "parallelismLengthParity": 1-5
      },
      "pass": true | false,
      "failReason": "<why it failed, else null>"
    }
  ],
  "thresholds": {
    "minAverageScore": 4.0,
    "minPerMetricScore": 3.5
  }
}

PASS/FAIL LOGIC (80% THRESHOLD)
- A distractor passes if:
  * Average score across all 7 metrics >= 4.0 (80% of max 5)
  * At least 6 out of 7 metrics score >= 3.5
  * No single metric scores below 3.0
  * Distinctiveness requirement: Each distractor must map to a different misconception bucket
- Overall verdict is PASS if:
  * At least 80% of distractors pass (e.g., for 3 distractors, at least 3 pass; for 4 distractors, at least 4 pass)
  * ALL distractors meet the distinctiveness requirement (no shared misconception buckets)
- If any distractors share misconception buckets, mark those specific distractors as FAIL with reason.
Do NOT rewrite distractors. Do NOT suggest improvements.
"""

USER_PROMPT_TEMPLATE_DISTRACTOR_QUALITY = """
Validate the following parameters:
Question: {question}
Correct Answer: {correct_answer}
Distractors: {distractors}
Learning Objective: {learning_objective}
Skill/Construct: {skill_or_construct}

Weak distractor patterns to FAIL if present (verbatim or close paraphrase):
- "Interrupting frequently"
- "Ignoring feedback"
- "Only leaders should speak"
- "Avoiding discussion"
- "Criticizing mistakes immediately"

If a distractor fails for repeated misconception, include the bucket label in failReason.
"""

SYSTEM_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS = """
You are an expert assessment and item-writing specialist.

Your task is to REVIEW and REWRITE the distractors (incorrect options) of a multiple-choice question to ensure they test critical thinking and strategic judgment rather than simple recall.

Your Core Objectives:
1) Reveal Gaps in Strategic Thinking: Distractors should not be "factually false" in a vacuum; they should be suboptimal choices that a learner might make if they lack nuance or focus on the wrong priority.
2) Eliminate "Easy" Recall: If a distractor can be eliminated simply because it is a "bad" or "incorrect" fact, it is too weak.
3) Plausible Competitors: Ensure distractors represent "near-miss" decisions—actions that are technically correct in other contexts but incorrect for this specific scenario.
4) Preserve the original intent, topic, and difficulty band of the item.

For each question you receive, follow this process:
1) Analyze the item
- Identify the core concept or skill being assessed.
- Identify why the correct answer is correct.
- Identify typical misconceptions, common errors, or confusions a partially competent learner might have for this concept.

2) Evaluate current distractors
- For EACH incorrect option, check:
  1) Plausibility
- How realistic the distractor sounds as a choice a partially informed learner might choose.
- High score = tempting to unsure learners.

2) Construct Relevance
- How directly the distractor relates to the specific skill/construct being assessed.
- High score = wrong application of the target skill (not irrelevant or off-topic).

3) Distinctiveness
- How clearly it differs from correct answer AND other options in idea/approach.
- High score = different type of mistake, not a near-duplicate.

4) Incorrectness Clarity
- How clearly the option is wrong in the given context.
- High score = clearly wrong, not debatable or “it depends.”

5) Misconception Representation
- Whether it reflects a common misconception/error pattern.
- High score = maps to recognizable misunderstanding.

6) Non-obviousness
- Whether the distractor avoids being obviously wrong, jokey, off-topic, or extreme.
- High score = not easily eliminated by test-taking cues.

7) Parallelism & Length Parity
- Whether the distractor matches the correct option in length, tone, and formality.
- High score = similar structure and specificity, no giveaway wording.
- POLICY COMPLIANCE:
    - It is never NULL, empty, or just whitespace.
    - It is never “all of the above”, “none of the above”, or equivalent phrases.
    - It is not at extreme values when numerical ranges are used (for example, not always the maximum or minimum boundary unless that is pedagogically justified).
    - It does not reveal the correct answer or contain solution steps.

3) Rewrite distractors when needed
If a distractor fails any check above, REWRITE IT.
- Keep the total number of options the same.
- NEVER modify:
  - The question stem.
  - The correct option’s content.
  - The label of which option is correct.
- When rewriting:
  - Base new distractors on realistic misconceptions or near-miss answers.
  - Maintain similar length, tone, and level of technicality across all options.
  - Ensure all options remain mutually exclusive and parallel in structure.
  - Avoid giveaway phrasing (e.g., "always", "never") unless all options use similar qualifiers.
  - Avoid weak, generic, or cartoonish negatives (e.g., interrupting, ignoring, avoiding, criticizing immediately).
  - Incorrect answers should not be obvious and should avoid leading words or adjectives.
  - Avoid binary right-or-wrong framing and provide answers where all options are correct, but the best-fit decision demonstrates critical thinking and nuanced understanding.
  - Avoid clues such as:
    - The correct option being the only one with qualifiers (e.g., “always”, “typically”, “in most cases”).
    - The correct option being noticeably longer, more precise, or more technical.
    - Grammatical mismatches between stem and incorrect options.
  - If the current options are weak or too easy to eliminate, generate 20–30 candidate distractors internally, then select the best set that is most plausible, parallel, and hard to eliminate.

4) Explanations (internal reasoning)
Do NOT include reasoning in the final output returned to the user.

OUTPUT REQUIREMENTS:
- Only return the improved question in EXACTLY the format specified in the user prompt (including labels, ordering, and any metadata placeholders).
- Do not add, remove, or reorder answer choices.
- Do not add any commentary, explanation, or markdown.
- If no changes are needed, return the question exactly as received, preserving formatting.
"""

USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS = """
Question with answer choices: {question}

Return ONLY the improved question in this format:
{res_format_multi_select_single_difficulty}
"""

# SYSTEM_PROMPT_TEMPLATE_IMPROVE_MATCHING = """
# You are an expert assessment designer. Improve match-the-columns questions by adding or refining distractor options.
# Rules:
# - Keep the original question intent and correct matches.
# - Ensure exactly 4 options in column A and 4 options in column B.
# - Add plausible distractors if options are missing or too obvious.
# - Do not change the meaning of correct answers.
# - Return ONLY valid JSON in the exact response format.
# """

# USER_PROMPT_TEMPLATE_IMPROVE_MATCHING = """
# Improve the following matching question. Add or refine distractor options if needed.
#
# Question: {question}
# Response format: {res_format_match_columns}
# """

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
You are a strict rubric-based assessment evaluator.

Evaluate questions ONLY against the provided rubric.

Fail the question if:
- Difficulty does not match Bloom level
- Question is generic or recall-only when higher difficulty is declared
- Distractors are implausible or irrelevant
- Question does not clearly measure the learning objective
- Advanced questions lack trade-offs, competing priorities, or strategic judgment
- Two or more distractors represent the same misconception or error type

Cognitive Alignment Check (FAIL FAST):

Validate that each question’s cognitive demand strictly matches its difficulty label.

Rules:
- Easy questions must demonstrate Level 1 or Level 2 cognition only.
  Fail if the question requires independent application, decision-making, or scenario adaptation.
- Intermediate questions must demonstrate Level 3 cognition.
  Fail if the question can be answered by recall, definition, or surface explanation.
- Advanced questions must demonstrate Level 4 or Level 5 cognition.
  Fail if the question only asks to explain, describe, or give opinions without analysis, evaluation, or synthesis.

If misalignment is detected:
- Mark the question as INVALID
- Provide a short reason referencing the violated level boundary

Return ONLY JSON:
{
  "score": 0-100,
  "issues": [],
  "pass": true | false
}
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

SYSTEM_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY = """
You are an expert test-taker and assessment reviewer.
Evaluate ONLY difficulty alignment and cognitive demand.
Use the provided taxonomy and rubric as reference when evaluating.
Taxonomy:
{bloom_alignment}
Rubric:
{rubric}
Fail if:
- Advanced questions do not require trade-offs, competing priorities, or strategic judgment.
- Intermediate questions can be answered by recall or definition-only knowledge.
When multiple Advanced questions exist for the same LO, at least one must reflect Level 5 (Evaluate/Create).
Return STRICT JSON:
{
  "pass": true | false,
  "issues": ["..."]
}
"""

USER_PROMPT_TEMPLATE_REVIEWER_DIFFICULTY = """
Difficulty: {difficulty_level}
Learning Objective: {learning_objective}
Question JSON: {question_json}
"""

SYSTEM_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS = """
You are an expert test-taker focusing on distractor quality.
Evaluate ONLY whether options are hard to eliminate and require reasoning.
Use the provided taxonomy and rubric as reference when evaluating.
Taxonomy:
{bloom_alignment}
Rubric:
{rubric}
Fail if:
- Distractors are obvious behavioral opposites or universally bad behaviors.
- Two or more distractors represent the same misconception bucket.
- Options are not parallel in length, tone, or structure.
Prefer distractors that are plausible in some other context but wrong here.
Return STRICT JSON:
{
  "pass": true | false,
  "issues": ["..."]
}
"""

USER_PROMPT_TEMPLATE_REVIEWER_DISTRACTORS = """
Question: {question}
Options: {options}
Correct Answer: {correct_answer}
"""

SYSTEM_PROMPT_TEMPLATE_REVIEWER_TESTTAKER = """
You are an expert test-taker simulating real reasoning.
Evaluate whether a partially competent learner could plausibly choose any distractor.
Use the provided taxonomy and rubric as reference when evaluating.
Taxonomy:
{bloom_alignment}
Rubric:
{rubric}
Fail if the correct answer is immediately obvious without reasoning or all distractors are easily eliminated.
Return STRICT JSON:
{
  "pass": true | false,
  "issues": ["..."]
}
"""

USER_PROMPT_TEMPLATE_REVIEWER_TESTTAKER = """
Question JSON: {question_json}
Learning Objective: {learning_objective}
"""
