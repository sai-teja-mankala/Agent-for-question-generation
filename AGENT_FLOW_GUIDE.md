# Question Generation Agent - Complete Flow Guide

## Overview

This document explains the complete flow of the question generation pipeline, showing the **input and output format at each agent step** with real examples.

---

## Pipeline Architecture

```
📋 PRE-GRAPH SETUP
   create_question_configs()
   ↓ (Creates configurations)

🤖 AGENT GRAPH
   build_scenario → build_question → build_options → improve → 
   validate_distractors ⟷ correct_distractors →
   validate_quality ⟷ correct_quality →
   END

📦 POST-GRAPH PROCESSING
   format_conversion → validate_and_fix_format → _build_output
```

---

## Step-by-Step Flow with Examples

### **STEP 0: API Input** (User Request)

**Location:** API endpoint receives request

**Input Format:**
```json
{
  "sourceText": "Ontario Power Generation (OPG) leaders drive safety and operational excellence...",
  "learningObjectives": [
    "Encourages cross-functional alignment on key initiatives.",
    "Tracks team progress, adjusts plans, and drives continuous improvement."
  ],
  "numberOfQuestions": 5,
  "questionTypes": ["MULTIPLE_CHOICE"],
  "difficultyLevels": ["Advanced"]
}
```

---

### **STEP 1: create_question_configs** (PRE-GRAPH)

**Location:** `run_pipeline()` - Before graph execution  
**Type:** Configuration Generator (No LLM calls)

**What It Does:**
- Calculates all combinations: LO × QuestionType × Difficulty
- Creates one config per question (questionsPerSet=1 by default)
- For 2 LOs × 1 Type × 1 Difficulty × 5 questions = **10 configs**

**Input:** API payload
```python
{
  "input": payload,
  "question_configs": [],
  "scenarios": [],
  "questions": [],
  "raw_outputs": [],
  "improved_outputs": [],
  "formatted": []
}
```

**Output (state):**
```python
{
  "input": {...},  # Original payload
  "question_configs": [
    {
      "learningObjective": "Encourages cross-functional alignment...",
      "difficultyLevel": "Advanced",
      "questionType": "MULTIPLE_CHOICE",
      "sourceText": "Ontario Power Generation...",
      "numCorrectOptions": 1,
      "numIncorrectOptions": 3,
      "numberOfQuestions": 1,
      "intermediateFormat": "{...}",
      "responseFormat": "{...}",
      "systemPrompt": "SYSTEM_CONTRACT...",
      "userPrompt": "",
      "baseUserPrompt": ""
    },
    // ... 9 more configs (one per question)
  ],
  "scenarios": [],
  "questions": [],
  "raw_outputs": [],
  "improved_outputs": [],
  "formatted": []
}
```

**Internal Process:**
```
For each LO:
  For each QuestionType:
    For each DifficultyLevel:
      For i in range(sets_per_config):
        Create config payload
```

---

### **STEP 2: build_scenario** (FIRST AGENT)

**Location:** First node in graph (Entry Point)  
**Type:** LLM Agent

**What It Does:**
- Generates realistic scenarios for Intermediate/Advanced questions
- Creates decision points for higher-order thinking
- Uses SCENARIO_GENERATION_PROMPT

**Input (state from previous step):**
```python
{
  "question_configs": [10 configs],  # From create_question_configs
  "scenarios": [],  # Empty
  ...
}
```

**Internal Process:**
```
For each config in question_configs:
  Extract: LO, difficulty, sourceText
  
  Call LLM:
    Prompt: SCENARIO_GENERATION_PROMPT
    Input: {
      "learning_objective": "Encourages cross-functional alignment...",
      "difficulty": "Advanced",
      "source_context": "Ontario Power Generation..."
    }
  
  Parse response:
    {
      "scenario": "A product manager at a tech company...",
      "decisionPoint": "How should the product manager evaluate..."
    }
```

**Output (state):**
```python
{
  "question_configs": [10 configs],
  "scenarios": [
    {
      "payload": {config_1},
      "scenario": "A product manager at a tech company is leading a new initiative to launch a mobile application. The marketing team wants to prioritize features that highlight brand visibility, while the engineering team is focused on technical feasibility...",
      "decisionPoint": "How should the product manager evaluate these competing priorities to encourage cross-functional alignment?"
    },
    // ... 9 more scenarios
  ],
  "questions": [],
  ...
}
```

**Example Output:**
```json
{
  "scenario": "A product manager at a tech company is leading a new initiative to launch a mobile application. The marketing team wants to prioritize features that highlight brand visibility, while the engineering team is focused on technical feasibility and minimal viable product.",
  "decisionPoint": "How should the product manager evaluate these competing priorities to encourage cross-functional alignment on the initiative?"
}
```

---

### **STEP 3: build_question** (SECOND AGENT)

**Location:** Second node in graph  
**Type:** LLM Agent

**What It Does:**
- Generates question text based on scenario
- Aligns with learning objective and difficulty
- Uses QUESTION_GENERATION_PROMPT

**Input (state from build_scenario):**
```python
{
  "question_configs": [10 configs],
  "scenarios": [10 scenarios],  # From build_scenario
  "questions": [],  # Empty
  ...
}
```

**Internal Process:**
```
For each scenario in scenarios:
  Extract: scenario, decisionPoint, LO, difficulty
  
  Call LLM:
    Prompt: QUESTION_GENERATION_PROMPT
    Input: {
      "learning_objective": "Encourages cross-functional alignment...",
      "difficulty": "Advanced",
      "scenario": "A product manager at a tech company...",
      "decision_point": "How should the product manager evaluate..."
    }
  
  Parse response:
    {
      "questionText": "A product manager at a tech company is leading..."
    }
```

**Output (state):**
```python
{
  "question_configs": [10 configs],
  "scenarios": [10 scenarios],
  "questions": [
    {
      "payload": {config_1},
      "scenario": "A product manager...",
      "decisionPoint": "How should...",
      "questionText": "A product manager at a tech company is leading a new initiative to launch a mobile application. The marketing team wants to prioritize features that highlight brand visibility, while the engineering team is focused on the technical feasibility and minimal viable product. How should the product manager evaluate these competing priorities to encourage cross-functional alignment on the initiative?"
    },
    // ... 9 more questions
  ],
  "raw_outputs": [],
  ...
}
```

---

### **STEP 4: build_options** (THIRD AGENT)

**Location:** Third node in graph  
**Type:** LLM Agent

**What It Does:**
- Generates answer options (1 correct + 3 distractors)
- Ensures distractors are plausible but incorrect
- Uses OPTIONS_GENERATION_PROMPT

**Input (state from build_question):**
```python
{
  "question_configs": [10 configs],
  "scenarios": [10 scenarios],
  "questions": [10 questions],  # From build_question
  "raw_outputs": [],  # Empty
  ...
}
```

**Internal Process:**
```
For each question in questions:
  Extract: questionText, scenario, numCorrect, numIncorrect
  
  Call LLM:
    Prompt: OPTIONS_GENERATION_PROMPT
    Input: {
      "question_text": "A product manager at a tech company...",
      "scenario": "...",
      "num_correct": 1,
      "num_incorrect": 3
    }
  
  Parse response:
    {
      "answers": [
        {"answerText": "Facilitate a cross-functional workshop...", "isCorrect": true, "explanation": "..."},
        {"answerText": "Prioritize features that balance...", "isCorrect": false, "explanation": "..."},
        {"answerText": "Conduct separate focus groups...", "isCorrect": false, "explanation": "..."},
        {"answerText": "Develop a phased rollout plan...", "isCorrect": false, "explanation": "..."}
      ]
    }
```

**Output (state):**
```python
{
  "question_configs": [10 configs],
  "scenarios": [10 scenarios],
  "questions": [10 questions],
  "raw_outputs": [
    {
      "payload": {config_1},
      "result": {
        "LearningObjective": "Encourages cross-functional alignment...",
        "questions": [
          {
            "questionText": "A product manager at a tech company...",
            "answer": [
              {
                "answerText": "Facilitate a cross-functional workshop to prioritize customer value.",
                "explanation": "This approach encourages alignment by focusing on shared customer-centric goals.",
                "isCorrect": true
              },
              {
                "answerText": "Prioritize features that balance technical feasibility and brand visibility.",
                "explanation": "Although this aims for balance, it may overshadow broader customer value drivers.",
                "isCorrect": false
              },
              // ... 2 more distractors
            ],
            "scenarioFocus": "A product manager at a tech company..."
          }
        ]
      },
      "quality": {"score": 100, "issues": [], "pass": true},
      "relevancy": {"score": 100, "issues": [], "pass": true}
    },
    // ... 9 more complete questions
  ],
  "improved_outputs": [],
  ...
}
```

---

### **STEP 5: improve_distractors** (FOURTH AGENT)

**Location:** Fourth node (improve)  
**Type:** LLM Agent

**What It Does:**
- Reviews and improves distractor quality
- Ensures distractors are plausible but clearly wrong
- Uses USER_PROMPT_TEMPLATE_CHECK_AND_IMPROVE_DISTRACTORS

**Input (state from build_options):**
```python
{
  "raw_outputs": [10 complete questions],  # From build_options
  "improved_outputs": [],  # Empty
  ...
}
```

**Internal Process:**
```
For each item in raw_outputs:
  Extract: payload, result (question with options)
  
  Call LLM:
    Prompt: CHECK_AND_IMPROVE_DISTRACTORS
    Input: {
      "question": {full question with options},
      "res_format": "{...}"
    }
  
  Parse response:
    {improved question with better distractors}
```

**Output (state):**
```python
{
  "raw_outputs": [10 questions],
  "improved_outputs": [
    {
      "payload": {config_1},
      "result": {
        "LearningObjective": "...",
        "questions": [{
          "questionText": "...",
          "answer": [
            // Improved distractors with better plausibility
            {"answerText": "...", "explanation": "...", "isCorrect": true},
            {"answerText": "...", "explanation": "...", "isCorrect": false},
            {"answerText": "...", "explanation": "...", "isCorrect": false},
            {"answerText": "...", "explanation": "...", "isCorrect": false}
          ]
        }]
      }
    },
    // ... 9 more improved questions
  ],
  ...
}
```

---

### **STEP 6: validate_distractors** (VALIDATION AGENT)

**Location:** Fifth node  
**Type:** LLM Validator

**What It Does:**
- Validates distractor quality against rubric
- Checks: plausibility, distinctiveness, construct relevance, misconception representation
- Scores each distractor: must achieve 80% to pass
- Uses DISTRACTOR_VALIDATION_PROMPT

**Input (state from improve):**
```python
{
  "improved_outputs": [10 improved questions],  # From improve
  "distractor_validation_passed": [],  # Empty initially
  "distractor_validation_failed": [],  # Empty initially
  ...
}
```

**Internal Process:**
```
For each item in improved_outputs:
  Extract: question with all distractors
  
  Call LLM:
    Prompt: DISTRACTOR_VALIDATION_PROMPT
    Input: {question with distractors}
  
  Parse response:
    {
      "overall_assessment": {...},
      "distractors": [
        {
          "distractor_text": "...",
          "plausibility_score": 8,
          "construct_relevance_score": 7,
          "distinctiveness_score": 9,
          ...
          "overall_score": 82,
          "pass": true
        },
        // ... scores for each distractor
      ]
    }
  
  Calculate: passed_count / total_count
  
  If >= 80% pass:
    Add to distractor_validation_passed
  Else:
    Add to distractor_validation_failed with reasons
```

**Output (state):**
```python
{
  "improved_outputs": [8 passed],  # Only passed items during loop
  "distractor_validation_passed": [
    {
      "payload": {config_1},
      "result": {question},
      "validation_result": {
        "overall_assessment": {...},
        "distractors": [{scores}],
        "pass_rate": 1.0
      }
    },
    // ... 7 more passed
  ],
  "distractor_validation_failed": [
    {
      "payload": {config_9},
      "result": {question},
      "validation_result": {...},
      "failed_questions": [
        {
          "index": 0,
          "question": {question data},
          "reasons": [
            "Distractor 2: Plausibility too low (score: 5/10)",
            "Distractor 3: Not distinct enough from correct answer"
          ]
        }
      ],
      "passed_questions": [],
      "question_count": 1
    },
    // ... 1 more failed
  ],
  "distractor_correction_attempts": 0,
  ...
}
```

**Example Validation Result:**
```json
{
  "overall_assessment": {
    "strength": "Distractors are contextually appropriate and plausible",
    "improvement_areas": ["Distractor 2 could be more distinct"],
    "pass": true
  },
  "distractors": [
    {
      "distractor_text": "Prioritize features that balance...",
      "plausibility_score": 8,
      "construct_relevance_score": 9,
      "distinctiveness_score": 7,
      "misconception_representation_score": 8,
      "parallelism_length_parity_score": 9,
      "overall_score": 82,
      "pass": true,
      "rationale": "Strong distractor with good plausibility"
    }
  ],
  "pass_rate": 1.0
}
```

---

### **STEP 7: correct_distractors** (CORRECTION AGENT)

**Location:** Correction node (if validation fails)  
**Type:** LLM Agent

**What It Does:**
- Receives failed questions with specific failure reasons
- Regenerates improved distractors based on feedback
- Sends corrected items back for re-validation
- Max 6 attempts

**Input (state from validate_distractors):**
```python
{
  "distractor_validation_failed": [
    {
      "payload": {...},
      "result": {question},
      "failed_questions": [
        {
          "index": 0,
          "question": {...},
          "reasons": [
            "Distractor 2: Plausibility too low",
            "Distractor 3: Not distinct enough"
          ]
        }
      ]
    }
  ],
  "distractor_correction_attempts": 1,
  ...
}
```

**Internal Process:**
```
For each failed_item in distractor_validation_failed:
  For each failed_question in failed_item.failed_questions:
    Extract: question, failure_reasons
    
    Build feedback:
      "Previous issues:
       - Distractor 2: Plausibility too low
       - Distractor 3: Not distinct enough"
    
    Call LLM:
      Prompt: DISTRACTOR_CORRECTION_PROMPT
      Input: {
        "question": {...},
        "feedback": "Previous issues...",
        "format": {...}
      }
    
    Parse response:
      {corrected question with improved distractors}
```

**Output (state):**
```python
{
  "improved_outputs": [2 corrected],  # ONLY corrected items for re-validation
  "distractor_validation_failed": [],  # Cleared
  "distractor_correction_attempts": 1,
  ...
}
```

**Flow:**
```
validate_distractors (2 failed) 
    ↓
correct_distractors (fix 2 items)
    ↓
validate_distractors again (re-validate 2 corrected items)
    ↓
Loop continues until all pass or max attempts (6) reached
```

---

### **STEP 8: validate_quality** (QUALITY VALIDATION AGENT)

**Location:** After distractor validation passes  
**Type:** LLM Validator

**What It Does:**
- Validates overall question quality and learning objective relevancy
- Checks: clarity, cognitive alignment, scenario realism, Bloom's taxonomy
- Must achieve 85% score to pass
- Uses QUALITY_VALIDATION_PROMPT

**Input (state after distractors validated):**
```python
{
  "improved_outputs": [10 questions],  # All passed distractor validation
  "quality_validation_passed": [],  # Empty initially
  "quality_validation_failed": [],  # Empty initially
  ...
}
```

**Internal Process:**
```
For each item in improved_outputs:
  Extract: question, learning_objective
  
  Call LLM:
    Prompt: QUALITY_VALIDATION_PROMPT
    Input: {
      "question": {...},
      "learning_objective": "..."
    }
  
  Parse response:
    {
      "quality": {
        "score": 88,
        "issues": [],
        "pass": true,
        "details": {
          "clarity_score": 9,
          "cognitive_alignment_score": 9,
          "scenario_realism_score": 8,
          "bloom_alignment": "Evaluate"
        }
      },
      "relevancy": {
        "score": 90,
        "issues": [],
        "pass": true
      }
    }
  
  If quality >= 85 AND relevancy >= 85:
    Add to quality_validation_passed
  Else:
    Add to quality_validation_failed with reasons
```

**Output (state):**
```python
{
  "improved_outputs": [9 passed],  # Only passed during loop
  "quality_validation_passed": [
    {
      "payload": {...},
      "result": {question},
      "quality": {
        "score": 88,
        "issues": [],
        "pass": true,
        "details": {...}
      },
      "relevancy": {
        "score": 90,
        "issues": [],
        "pass": true
      }
    },
    // ... 8 more passed
  ],
  "quality_validation_failed": [
    {
      "payload": {...},
      "result": {question},
      "quality": {
        "score": 78,
        "issues": ["Question lacks sufficient cognitive challenge"],
        "pass": false
      },
      "relevancy": {
        "score": 85,
        "issues": [],
        "pass": true
      }
    }
  ],
  "quality_correction_attempts": 0,
  ...
}
```

---

### **STEP 9: correct_quality** (QUALITY CORRECTION AGENT)

**Location:** Correction node (if quality validation fails)  
**Type:** LLM Agent

**What It Does:**
- Receives failed questions with quality/relevancy issues
- Regenerates improved questions based on feedback
- Max 6 attempts

**Input (state from validate_quality):**
```python
{
  "quality_validation_failed": [
    {
      "payload": {...},
      "result": {question},
      "quality": {
        "score": 78,
        "issues": ["Lacks cognitive challenge"],
        "pass": false
      }
    }
  ],
  "quality_correction_attempts": 1,
  ...
}
```

**Internal Process:**
```
For each failed_item in quality_validation_failed:
  Extract: question, quality_issues, relevancy_issues
  
  Build feedback:
    "Quality issues:
     - Lacks sufficient cognitive challenge
     Current score: 78/100"
  
  Call LLM:
    Prompt: QUALITY_CORRECTION_PROMPT
    Input: {
      "question": {...},
      "feedback": "Quality issues...",
      "learning_objective": "..."
    }
  
  Parse response:
    {improved question}
```

**Output (state):**
```python
{
  "improved_outputs": [1 corrected],  # ONLY corrected item
  "quality_validation_failed": [],  # Cleared
  "quality_correction_attempts": 1,
  ...
}
```

**Flow:**
```
validate_quality (1 failed)
    ↓
correct_quality (fix 1 item)
    ↓
validate_quality again (re-validate 1 corrected)
    ↓
Loop continues until all pass or max attempts (6) reached
```

---

### **STEP 10: Final Merge & Exit**

**Location:** Routing functions  
**Type:** State Management

**What Happens:**
When validation loops exit (all passed or max attempts):

**In `_route_from_validate_quality`:**
```python
if failed and attempts >= max_attempts:
    # Max attempts reached - merge ALL items (passed + failed)
    passed_outputs = [
        {"payload": e["payload"], "result": e["result"]}
        for e in state["quality_validation_passed"]
    ]
    failed_outputs = [
        {"payload": e["payload"], "result": e["result"]}
        for e in failed
    ]
    state["improved_outputs"] = passed_outputs + failed_outputs
```

**Final State:**
```python
{
  "improved_outputs": [
    # All 10 questions (9 passed + 1 improved through 6 attempts)
    {"payload": {...}, "result": {question_1}},
    {"payload": {...}, "result": {question_2}},
    // ... all 10 questions
  ],
  ...
}
```

---

### **STEP 11: format_conversion** (POST-GRAPH)

**Location:** `run_pipeline()` after graph execution  
**Type:** Formatter (No LLM)

**What It Does:**
- Converts internal format to API output format
- Adds UUIDs for questions and answers
- Normalizes field names

**Input:**
```python
{
  "improved_outputs": [
    {
      "payload": {
        "learningObjective": "...",
        "difficultyLevel": "Advanced",
        "questionType": "MULTIPLE_CHOICE"
      },
      "result": {
        "LearningObjective": "...",
        "questions": [{...}]
      }
    }
  ]
}
```

**Output:**
```python
{
  "formatted": [
    {
      "payload": {...},
      "learningObjective": "Encourages cross-functional alignment...",
      "difficultyLevel": "Advanced",
      "questionType": "MULTIPLE_CHOICE",
      "result": {
        "questions": [
          {
            "id": "6948b26a-dac8-4d21-a79d-f1f243d84ade",
            "questionType": "MULTIPLE_CHOICE",
            "aiGeneratedDifficulty": "Advanced",
            "questionText": "A product manager...",
            "answer": [
              {
                "answerId": "ca0a9147-427c-4051-a484-0ef02d9419ef",
                "answerText": "Facilitate a cross-functional workshop...",
                "explanation": "...",
                "isCorrect": true
              },
              // ... 3 distractors with UUIDs
            ],
            "scenarioFocus": "..."
          }
        ]
      }
    }
  ]
}
```

---

### **STEP 12: _build_output** (FINAL FORMAT)

**Location:** `run_pipeline()` at the end  
**Type:** Output Builder (No LLM)

**What It Does:**
- Groups questions by learning objective
- Creates final API response structure
- Adds metadata

**Input:**
```python
{
  "formatted": [10 formatted questions]
}
```

**Output (Final API Response):**
```json
{
  "learningObjectives": [
    {
      "learningObjective": "Encourages cross-functional alignment on key initiatives.",
      "learningObjectiveUuid": null,
      "learningObjectiveOrder": 1,
      "questions": [
        {
          "id": "6948b26a-dac8-4d21-a79d-f1f243d84ade",
          "questionType": "MULTIPLE_CHOICE",
          "aiGeneratedDifficulty": "Advanced",
          "questionText": "A product manager at a tech company...",
          "answer": [
            {
              "answerId": "ca0a9147-427c-4051-a484-0ef02d9419ef",
              "answerText": "Facilitate a cross-functional workshop to prioritize customer value.",
              "explanation": "This approach encourages alignment...",
              "isCorrect": true
            },
            {
              "answerId": "28760485-26aa-4ea4-a35d-1b9b3409c625",
              "answerText": "Prioritize features that balance...",
              "explanation": "Although this aims for balance...",
              "isCorrect": false
            },
            {
              "answerId": "f712cb12-eeca-41e2-b175-757a2cb6d29a",
              "answerText": "Conduct separate focus groups...",
              "explanation": "This may provide insight...",
              "isCorrect": false
            },
            {
              "answerId": "04c332a7-6ec9-48d0-8719-5fda32bdec4f",
              "answerText": "Develop a phased rollout plan...",
              "explanation": "A phased plan may defer alignment...",
              "isCorrect": false
            }
          ],
          "isUploaded": false,
          "scenarioFocus": null
        }
        // ... 4 more questions for this LO
      ]
    },
    {
      "learningObjective": "Tracks team progress, adjusts plans, and drives continuous improvement.",
      "learningObjectiveUuid": null,
      "learningObjectiveOrder": 2,
      "questions": [
        // ... 5 questions for second LO
      ]
    }
  ],
  "questionGenerationStatus": "READY_FOR_REVIEW"
}
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      API REQUEST                                 │
│  {sourceText, learningObjectives, numberOfQuestions, ...}        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 0: create_question_configs                     │
│                    (PRE-GRAPH SETUP)                             │
│  Input:  API payload                                             │
│  Output: State with question_configs [10 configs]                │
│  Type:   Configuration Generator (No LLM)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ╔════════════════════════════════════════════╗
        ║        AGENT GRAPH EXECUTION               ║
        ╚════════════════════════════════════════════╝
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: build_scenario                              │
│                   (ENTRY POINT - First LLM Agent)                │
│  Input:  question_configs [10]                                   │
│  Process: LLM generates scenarios + decision points              │
│  Output: scenarios [10]                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: build_question                              │
│                   (Second LLM Agent)                             │
│  Input:  scenarios [10]                                          │
│  Process: LLM generates question text                            │
│  Output: questions [10]                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 3: build_options                               │
│                   (Third LLM Agent)                              │
│  Input:  questions [10]                                          │
│  Process: LLM generates 1 correct + 3 distractors                │
│  Output: raw_outputs [10 complete questions]                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 4: improve_distractors                         │
│                   (Fourth LLM Agent)                             │
│  Input:  raw_outputs [10]                                        │
│  Process: LLM improves distractor quality                        │
│  Output: improved_outputs [10]                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ╔════════════════════════════════════════════╗
        ║     DISTRACTOR VALIDATION LOOP             ║
        ╚════════════════════════════════════════════╝
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         │
┌──────────────────────┐                         │
│  validate_distractors│                         │
│  (Validation Agent)  │                         │
│                      │                         │
│ 80% threshold check  │                         │
│ Scores each          │                         │
│ distractor           │                         │
└─────┬────────┬───────┘                         │
      │        │                                  │
 Pass │        │ Fail & attempts < 6              │
      │        │                                  │
      │        ▼                                  │
      │  ┌─────────────────────┐                 │
      │  │ correct_distractors │                 │
      │  │ (Correction Agent)  │                 │
      │  │                     │                 │
      │  │ Fix based on        │                 │
      │  │ feedback            │                 │
      │  └──────────┬──────────┘                 │
      │             │                            │
      │             └────────────────────────────┘
      │               (Re-validate)
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│           All distractors validated (or max attempts)            │
│  improved_outputs = passed + failed (if max attempts)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ╔════════════════════════════════════════════╗
        ║      QUALITY VALIDATION LOOP               ║
        ╚════════════════════════════════════════════╝
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         │
┌──────────────────────┐                         │
│  validate_quality    │                         │
│  (Validation Agent)  │                         │
│                      │                         │
│ 85% threshold check  │                         │
│ Quality + Relevancy  │                         │
│ Bloom's alignment    │                         │
└─────┬────────┬───────┘                         │
      │        │                                  │
 Pass │        │ Fail & attempts < 6              │
      │        │                                  │
      │        ▼                                  │
      │  ┌─────────────────────┐                 │
      │  │  correct_quality    │                 │
      │  │ (Correction Agent)  │                 │
      │  │                     │                 │
      │  │ Improve based on    │                 │
      │  │ feedback            │                 │
      │  └──────────┬──────────┘                 │
      │             │                            │
      │             └────────────────────────────┘
      │               (Re-validate)
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│           All quality validated (or max attempts)                │
│  improved_outputs = passed + failed (if max attempts)            │
│                       [10 final questions]                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ╔════════════════════════════════════════════╗
        ║      POST-GRAPH PROCESSING                 ║
        ╚════════════════════════════════════════════╝
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              format_conversion                                   │
│  Add UUIDs, normalize field names                                │
│  Output: formatted [10]                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              validate_and_fix_format                             │
│  Validate JSON structure, fix if needed                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              _build_output                                       │
│  Group by learning objective                                     │
│  Create final API response                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API RESPONSE                                │
│  {                                                               │
│    learningObjectives: [                                         │
│      {LO1: 5 questions},                                         │
│      {LO2: 5 questions}                                          │
│    ],                                                            │
│    questionGenerationStatus: "READY_FOR_REVIEW"                  │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Points

### State Flow
- **Pre-Graph**: `create_question_configs` populates `question_configs`
- **Graph Entry**: State with configs passed to first agent
- **Agent Chain**: Each agent reads from state, processes, writes to state
- **Validation Loops**: Failed items recirculate with feedback
- **Final Merge**: All items (passed + improved failed) in `improved_outputs`
- **Post-Graph**: Format conversion and output building

### Data Transformation
```
API Input → Configs → Scenarios → Questions → Options → 
Improved → Validated Distractors → Validated Quality → 
Formatted → Grouped by LO → API Output
```

### Quality Assurance
- **80% threshold** for distractor validation
- **85% threshold** for quality validation
- **Max 6 attempts** for corrections
- **Feedback loop** ensures continuous improvement
- **Failed items included** after max attempts (they've been improved)

---

## Summary

This pipeline ensures high-quality question generation through:
1. **Decomposed generation** (scenario → question → options)
2. **Multi-stage improvement** (improve_distractors)
3. **Rigorous validation** (distractors + quality)
4. **Feedback-driven correction** (up to 6 attempts)
5. **Complete output** (all questions, even if not perfect after max attempts)

Each agent has a clear responsibility, and the state flows cleanly through the pipeline with proper validation and correction loops.
