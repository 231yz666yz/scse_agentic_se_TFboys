import json
from ollama import chat

MODEL = "qwen3:8b"

## Create a system prompt for the Reviewer Agent that instructs it to analyze the simulation report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that "needs_revision" is a boolean.

REQUIRED_KEYS = {"issue", "likely_cause", "recommendation", "needs_revision"}

SYSTEM_PROMPT = """You are a Reviewer Agent in a multi-agent system. Your role is to review the simulation report of a robot's navigation logic and identify problems and improvements.

## Your Task
You will receive a simulation report (JSON) that contains:
- "total_scenarios": total number of test scenarios
- "passed_scenarios": number of scenarios that passed
- "failed_scenarios": number of scenarios that failed
- "success_rate": passed / total
- "results": a list of per-scenario results, each with "scenario" (description), "state" (sensor input), "expected" (expected action), "actual" (actual action), "passed" (boolean)

Analyze the report and identify problems with the navigation logic based on the failed scenarios.

## Output Format
Respond with ONLY a valid JSON object, no markdown, no code fences, no explanation. The JSON must have exactly these keys:

{
  "issue": "<a precise description of the problem found; if no failures, state that the logic passed all scenarios>",
  "likely_cause": "<the most likely cause of the problem based on the failed scenarios>",
  "recommendation": "<a concrete, actionable improvement suggestion for the developer>",
  "needs_revision": <true or false>
}

## Rules
1. "needs_revision" must be true if ANY scenario failed (success_rate < 1.0), otherwise false.
2. If there are failures, "issue" must reference the specific failed scenarios and what went wrong.
3. "likely_cause" must explain the pattern behind the failures (e.g., priority order of rules, missing blocked-direction checks).
4. "recommendation" must state precisely how the logic should be changed/fixed.
5. Output ONLY the JSON object. Do not wrap it in markdown or add any text before or after.
"""


## Create a function to validate the output of the Reviewer Agent.
## It should check that the output is a JSON object with the required keys and that "needs_revision" is a boolean, and the rest of the keys are strings.

def validate_review(result):
    if not isinstance(result, dict):
        raise ValueError(f"Expected a dict, got {type(result).__name__}")

    keys = set(result.keys())
    missing = REQUIRED_KEYS - keys
    extra = keys - REQUIRED_KEYS

    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected extra keys: {sorted(extra)}")

    if not isinstance(result["needs_revision"], bool):
        raise ValueError(f"'needs_revision' must be a boolean, got {type(result['needs_revision']).__name__}")

    for key in ("issue", "likely_cause", "recommendation"):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string")

    return True


## Create a function to run the Reviewer Agent.
## It should take in the simulation report, send it to the Reviewer Agent, and return the validated output.

def run_reviewer(simulation_report):
    user_content = json.dumps(simulation_report, ensure_ascii=False)

    response = chat(
        model=MODEL,
        think=False,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw_output = response["message"]["content"].strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.split("```", 2)[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        review = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Reviewer Agent did not return valid JSON: {e}\nRaw output: {raw_output}")

    validate_review(review)

    return review


if __name__ == "__main__":
    with open("artifacts/simulation_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    review = run_reviewer(report)
    print(json.dumps(review, indent=2))
