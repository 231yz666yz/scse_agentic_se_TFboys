import json
from ollama import chat

MODEL = "qwen3:8b"

## Create a system prompt for the Reviewer Agent that instructs it to analyze the IR-SIM Benchmark report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that w"safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans.

REQUIRED_KEYS = {"issue", "likely_cause", "recommendation",
                 "safety_passed", "goal_completion_passed", "efficiency_passed", "needs_revision"}

BOOLEAN_KEYS = {"safety_passed", "goal_completion_passed", "efficiency_passed", "needs_revision"}
STRING_KEYS = {"issue", "likely_cause", "recommendation"}

SYSTEM_PROMPT = """You are a Benchmark Reviewer Agent in a multi-agent system. Your role is to review the IR-SIM benchmark report of a robot's navigation logic and assess quality requirements: safety, goal completion, and efficiency.

## Your Task
You will receive a JSON object containing:
1. "benchmark_report": measured results across several IR-SIM worlds, including:
   - "total_worlds", "goals_reached", "success_rate"
   - "efficient_worlds", "inefficient_success_worlds", "failed_worlds", "efficiency_rate"
   - "average_steps_taken"
   - "results": per-world results with "reached_goal", "collision_or_done", "steps_taken", "efficiency_status"
2. "deterministic_review": a pre-computed review with the correct pass/fail booleans derived from the measurements.

## Output Format
Respond with ONLY a valid JSON object, no markdown, no code fences, no explanation. The JSON must have exactly these keys:

{
  "issue": "<precise description of the problem found>",
  "likely_cause": "<most likely cause of the problem>",
  "recommendation": "<concrete, actionable fix/improvement>",
  "safety_passed": <true or false>,
  "goal_completion_passed": <true or false>,
  "efficiency_passed": <true or false>,
  "needs_revision": <true or false>
}

## Rules
1. You MUST copy the values of "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" EXACTLY from the "deterministic_review". Never invent or alter these booleans.
2. "needs_revision" must be true if any of the three quality gates failed.
3. "issue" must state precisely what issue was found (e.g., which world failed, collision, inefficiency). If everything passed, state that the benchmark passed all quality gates.
4. "likely_cause" must explain the likely navigation-logic weakness behind the issue.
5. "recommendation" must specify how the navigation logic should be revised.
6. Output ONLY the JSON object. Do not wrap it in markdown or add any text before or after.
"""


## Create a function to validate the output of the Reviewer Agent for the benchmark report.
## It should check that the output is a JSON object with the required keys and that "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans, and the rest of the keys are strings.
## If the output does not meet these criteria, raise a ValueError.

def validate_benchmark_review(result):
    if not isinstance(result, dict):
        raise ValueError(f"Expected a dict, got {type(result).__name__}")

    keys = set(result.keys())
    missing = REQUIRED_KEYS - keys
    extra = keys - REQUIRED_KEYS

    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected extra keys: {sorted(extra)}")

    for key in BOOLEAN_KEYS:
        if not isinstance(result[key], bool):
            raise ValueError(f"'{key}' must be a boolean, got {type(result[key]).__name__}")

    for key in STRING_KEYS:
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string")

    return True


## Create a function to build a deterministic review from the benchmark report.
## This function analyzes the benchmark report and determines the values for "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" based on the measured benchmark fields.
## It returns a dictionary with the keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## If the benchmark report does not contain the required fields, default values will be used.
## If safety_passed is false, the issue will be described as "Unsafe benchmark behavior detected".
## Safety is measured as any world having collision_or_done true while reached_goal is false.
## If goal_completion_passed is false, the issue will be described as "Goal completion failure".
## Goal completion is measured as success_rate being less than 1.0.
## If efficiency_passed is false, the issue will be described as "Successful but inefficient navigation".
## Efficiency is measured as inefficient_success_worlds being greater than 0 or efficiency_rate being less than 1.0.

def build_deterministic_review(benchmark_report):
    if not isinstance(benchmark_report, dict):
        benchmark_report = {}

    results = benchmark_report.get("results", [])
    if not isinstance(results, list):
        results = []

    unsafe_worlds = [
        r for r in results
        if isinstance(r, dict)
        and r.get("collision_or_done") is True
        and r.get("reached_goal") is not True
    ]
    safety_passed = len(unsafe_worlds) == 0

    success_rate = benchmark_report.get("success_rate")
    if not isinstance(success_rate, (int, float)):
        success_rate = 0.0
    goal_completion_passed = success_rate >= 1.0

    inefficient_success_worlds = benchmark_report.get("inefficient_success_worlds")
    if not isinstance(inefficient_success_worlds, int):
        inefficient_success_worlds = 0
    efficiency_rate = benchmark_report.get("efficiency_rate")
    if not isinstance(efficiency_rate, (int, float)):
        efficiency_rate = 0.0
    efficiency_passed = inefficient_success_worlds == 0 and efficiency_rate >= 1.0

    needs_revision = not (safety_passed and goal_completion_passed and efficiency_passed)

    issues = []
    causes = []
    recommendations = []

    if not safety_passed:
        issues.append("Unsafe benchmark behavior detected")
        causes.append(
            "The robot collided or terminated abnormally before reaching the goal in: "
            + ", ".join(
                f"world {i + 1}" for i, r in enumerate(results)
                if isinstance(r, dict)
                and r.get("collision_or_done") is True
                and r.get("reached_goal") is not True
            )
        )
        recommendations.append(
            "Strengthen obstacle handling in decide_next_move: ensure blocked directions "
            "are never entered and STOP is returned when no safe direction exists."
        )

    if not goal_completion_passed:
        issues.append("Goal completion failure")
        causes.append(
            f"success_rate is {success_rate}, meaning some worlds ended without reaching the goal "
            "(e.g., premature STOP or endless turning)."
        )
        recommendations.append(
            "Make the robot prefer FORWARD toward the goal when the front is clear and only "
            "STOP when all directions are blocked."
        )

    if not efficiency_passed:
        issues.append("Successful but inefficient navigation")
        causes.append(
            f"inefficient_success_worlds={inefficient_success_worlds}, efficiency_rate={efficiency_rate}; "
            "the robot reached the goal but took too many steps (likely excessive turning)."
        )
        recommendations.append(
            "Reduce unnecessary turning: commit to the goal direction and avoid oscillating "
            "between LEFT and RIGHT when the path toward the goal is clear."
        )

    if not issues:
        issues.append("No issues detected: all benchmark quality gates passed")
        causes.append("All worlds reached the goal safely and efficiently.")
        recommendations.append(
            "No revision required. Keep the current navigation logic."
        )

    return {
        "issue": " | ".join(issues),
        "likely_cause": " ".join(causes),
        "recommendation": " ".join(recommendations),
        "safety_passed": safety_passed,
        "goal_completion_passed": goal_completion_passed,
        "efficiency_passed": efficiency_passed,
        "needs_revision": needs_revision,
    }


## Create a function to run the Reviewer Agent for the benchmark report.
## It should take in the benchmark report, build a deterministic review, send both to the Reviewer Agent, and return the validated output.
## The deterministic review is used to ensure that the pass/fail booleans in the output are based on the measured benchmark results, even if the LLM phrases the issue, likely cause, and recommendation.

def run_benchmark_reviewer(benchmark_report):
    deterministic_review = build_deterministic_review(benchmark_report)

    user_content = json.dumps({
        "benchmark_report": benchmark_report,
        "deterministic_review": deterministic_review,
    }, ensure_ascii=False)

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
        raise ValueError(f"Benchmark Reviewer Agent did not return valid JSON: {e}\nRaw output: {raw_output}")

    validate_benchmark_review(review)

    for key in BOOLEAN_KEYS:
        review[key] = deterministic_review[key]

    return review


if __name__ == "__main__":
    with open("artifacts/irsim_benchmark_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    review = run_benchmark_reviewer(report)
    print(json.dumps(review, indent=2))
