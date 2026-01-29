# Step-by-Step Output Logging Guide

## Overview

The question generation pipeline now logs detailed output from every major step to help with debugging and monitoring. All logs are written to a JSONL file (JSON Lines format - one JSON object per line).

## Log Files

### 1. **`step_outputs_log.jsonl`** (NEW - Main Step Output Log)
- **Format**: JSONL (one JSON object per line)
- **Purpose**: Tracks output from each major pipeline step
- **Cleared**: At the start of each pipeline run
- **Location**: Project root directory

### 2. **`build_prompts_log.json`**
- **Format**: Pretty-printed JSON
- **Purpose**: Details of all prompt payloads created
- **Created**: During `build_prompt_payloads` step
- **Location**: Project root directory

### 3. **`result_YYYYMMDD_HHMMSS.json`**
- **Format**: Pretty-printed JSON
- **Purpose**: Final API response for each run
- **Created**: When API endpoint returns
- **Location**: Project root directory

### 4. **`final_state.json`**
- **Format**: Pretty-printed JSON
- **Purpose**: Complete final state of the pipeline
- **Updated**: At the end of each run
- **Location**: Project root directory

---

## Steps Being Logged

The following pipeline steps are logged to `step_outputs_log.jsonl`:

| Step | Description | Key Data Logged |
|------|-------------|-----------------|
| **1. build_prompt_payloads** | Creates payloads for generation | Total payloads, configurations (type, difficulty, count) |
| **2. build_scenario** | Generates scenarios | Total scenarios, scenario lengths, decision points |
| **3. build_question** | Generates question text | Total questions, question lengths |
| **4. build_options** | Generates answer options | Total outputs, answer counts, question previews |
| **5. improve_distractors** | Improves distractor quality | Total improved, error status |
| **6. validate_distractors** | Validates distractor quality | Pass/fail counts, 80% threshold results, failure details |
| **7. validate_quality** | Validates overall quality | Pass/fail counts, quality/relevancy scores |
| **8. FINAL_OUTPUT** | Complete pipeline result | Total questions, breakdown by LO, full output data |

---

## Log Entry Format

Each line in `step_outputs_log.jsonl` is a JSON object with this structure:

```json
{
  "timestamp": "2026-01-29T12:30:45.123456",
  "step": "validate_distractors",
  "summary": {
    "newly_passed": 10,
    "total_passed": 15,
    "failed": 2,
    "validation_details": [...]
  },
  "full_data": null
}
```

### Fields:
- **`timestamp`**: ISO format timestamp
- **`step`**: Name of the pipeline step
- **`summary`**: Key metrics and preview data
- **`full_data`**: Complete data (only for FINAL_OUTPUT step)

---

## Example: Reading the Log

### Using Python:

```python
import json
from pathlib import Path

# Read all steps
log_file = Path("step_outputs_log.jsonl")
steps = []
with log_file.open("r") as f:
    for line in f:
        steps.append(json.loads(line))

# Print summary of each step
for step in steps:
    print(f"{step['timestamp']} - {step['step']}")
    print(f"  Summary: {step['summary']}")
```

### Using Command Line:

```bash
# View all steps
cat step_outputs_log.jsonl | jq .

# View only step names
cat step_outputs_log.jsonl | jq -r '.step'

# View validation results
cat step_outputs_log.jsonl | jq 'select(.step | contains("validate"))'

# View final output summary
cat step_outputs_log.jsonl | jq 'select(.step == "FINAL_OUTPUT") | .summary'
```

---

## Example Log Outputs

### 1. Build Prompt Payloads
```json
{
  "timestamp": "2026-01-29T12:30:00.000",
  "step": "build_prompt_payloads",
  "summary": {
    "total_payloads": 12,
    "configurations": [
      "MULTIPLE_CHOICE | easy | Q:3",
      "MULTIPLE_CHOICE | Intermediate | Q:3",
      "MULTIPLE_CHOICE | Advanced | Q:3"
    ]
  }
}
```

### 2. Validate Distractors
```json
{
  "timestamp": "2026-01-29T12:31:15.000",
  "step": "validate_distractors",
  "summary": {
    "newly_passed": 10,
    "total_passed": 10,
    "failed": 2,
    "validation_details": [
      {
        "difficulty": "Advanced",
        "question_type": "MULTIPLE_CHOICE",
        "passed_count": 1,
        "failed_count": 2
      }
    ]
  }
}
```

### 3. Validate Quality
```json
{
  "timestamp": "2026-01-29T12:32:00.000",
  "step": "validate_quality",
  "summary": {
    "newly_passed": 10,
    "total_passed": 10,
    "failed": 0,
    "quality_details": []
  }
}
```

### 4. Final Output
```json
{
  "timestamp": "2026-01-29T12:32:30.000",
  "step": "FINAL_OUTPUT",
  "summary": {
    "status": "READY_FOR_REVIEW",
    "total_learning_objectives": 2,
    "total_questions_generated": 12,
    "questions_by_lo": [
      {
        "lo": "Understand Python basics",
        "question_count": 6,
        "question_types": ["MULTIPLE_CHOICE"]
      }
    ]
  },
  "full_data": { ... complete output ... }
}
```

---

## Debugging Tips

### Check if questions are being lost:
```bash
# Count questions at each step
grep -o '"total_.*": [0-9]*' step_outputs_log.jsonl
```

### Find validation failures:
```bash
# See all failed validations
cat step_outputs_log.jsonl | jq 'select(.summary.failed > 0)'
```

### Track a specific learning objective:
```bash
# Search in final output
cat step_outputs_log.jsonl | jq 'select(.step == "FINAL_OUTPUT") | .summary.questions_by_lo[] | select(.lo | contains("Python"))'
```

### Monitor quality scores:
```bash
# Extract quality scores from validation
cat step_outputs_log.jsonl | jq 'select(.step == "validate_quality") | .summary.quality_details[].quality_score'
```

---

## File Size Management

- **`step_outputs_log.jsonl`**: Cleared at the start of each run (contains only the last run)
- **`result_*.json`**: One file per API call (accumulates over time - manual cleanup needed)
- **`build_prompts_log.json`**: Overwritten each run
- **`final_state.json`**: Overwritten each run

### Cleanup Script:

```bash
# Clean up old result files (keep last 10)
ls -t result_*.json | tail -n +11 | xargs rm -f

# Or clean all result files older than 7 days
find . -name "result_*.json" -mtime +7 -delete
```

---

## Benefits

✅ **Complete Audit Trail**: Every step's output is logged
✅ **Easy Debugging**: Quickly find where questions are lost or fail validation
✅ **Performance Monitoring**: Track how many items pass/fail at each stage
✅ **Historical Record**: Keep timestamped results for comparison
✅ **Machine Readable**: JSONL format for easy parsing and analysis

---

## Integration with Monitoring Tools

The JSONL format is compatible with:
- **Elasticsearch/Logstash**: Direct ingestion
- **Splunk**: Import as JSON events
- **Python Pandas**: `pd.read_json(log_file, lines=True)`
- **jq**: Command-line JSON processor
- **Custom Scripts**: Easy to parse line-by-line

---

## Questions?

If you need additional data logged at any step, the logging function is:

```python
_log_step_output(
    step_name="my_step",
    output_summary={"key": "value"},
    full_data=optional_complete_data
)
```

Add this call at the end of any node function in `agent.py`.
