import json
from ollama import chat

MODEL = "qwen3:8b"

### Create a system prompt that instructs the Test Agent to generate pytest-style tests for the decide_next_move function, 
# based on the requirements and plan provided. 
# The prompt should specify the expected input structure and required test coverage, while also enforcing constraints on the output format.
SYSTEM_PROMPT = """You are a Test Agent in a multi-agent system. Your role is to generate comprehensive pytest-style tests for the `decide_next_move` function.

## Your Task
Given the requirements artifact and the plan artifact, produce a complete pytest test file that tests the `decide_next_move(state)` function for ALL possible scenarios.

## Input
You will receive a JSON object containing:
- "requirements": {goal, allowed_actions, safe_stop, avoid_obstacles}
- "plan": {strategy, decisions, stop_point}

## Sensor State
The `state` dictionary has exactly these six boolean keys:
- "goal_ahead": the goal lies ahead (forward direction)
- "goal_on_left": the goal lies to the left
- "goal_on_right": the goal lies to the right
- "front_blocked": obstacle blocks forward
- "left_blocked": obstacle blocks left
- "right_blocked": obstacle blocks right

## Allowed Actions
FORWARD, LEFT, RIGHT, STOP

## Test Coverage Requirements
The expected behavior derived from the brief is: STOP only when front, left AND right
are ALL blocked; when the front is blocked but a side is clear, turn to a clear side,
preferring the side where the goal lies (default LEFT when the goal is ahead or not
sensed); otherwise prefer moving toward the goal; never turn into a blocked direction.
Your tests MUST cover ALL of the following scenarios:
1. Goal ahead, all clear -> FORWARD
2. Goal on left, all clear -> LEFT
3. Goal on right, all clear -> RIGHT
4. No goal sensed, all clear -> FORWARD (default)
5. Front blocked, sides clear -> LEFT (default evade side, never freeze)
6. Front and left blocked, right clear -> RIGHT
7. Front and right blocked, left clear -> LEFT
8. All three directions blocked -> STOP (only STOP case)
9. Goal ahead, front blocked -> LEFT (evasion dominates goal direction)
10. Goal ahead, front clear, side blocked -> FORWARD
11. Goal on left, left blocked -> RIGHT (never turn into blocked)
12. Goal on right, right blocked -> LEFT
13. Goal on left, front blocked -> LEFT (evade toward the goal side)
14. Goal on right, front blocked -> RIGHT (evade toward the goal side)
15. Both sides blocked, front clear -> FORWARD
16. The function must always return one of FORWARD, LEFT, RIGHT, STOP

## Output Format
Respond with ONLY a Python file. No markdown fences, no explanation.
The test file must:
1. Use `import pytest` and `import importlib.util`
2. Load the module from "generated/navigation_logic.py" dynamically
3. Define a `make_state()` helper for building state dicts
4. Use parametrized tests or individual test functions
5. Assert that each result is in {FORWARD, LEFT, RIGHT, STOP}
6. Assert specific expected actions for each scenario
7. Include a test that checks the function handles missing keys gracefully
"""

def validate_test_code(code):
    if not isinstance(code, str):
        raise ValueError(f"Invalid type: expected str, got {type(code).__name__}")
    if not code.strip():
        raise ValueError("Test code must not be empty")

    if code.strip().startswith("```"):
        raise ValueError("Test code must not be wrapped in markdown fences")

    required_keywords = [
        "import",
        "decide_next_move",
        "def test_",
        "assert",
    ]
    for kw in required_keywords:
        if kw not in code:
            raise ValueError(f"Test code must contain '{kw}'")

    try:
        compile(code, filename="<test_code>", mode="exec")
    except SyntaxError as e:
        raise ValueError(f"Test code is not valid Python: {e}")

    return True

def run_test_agent(requirements, plan):
    user_content = json.dumps({
        "requirements": requirements,
        "plan": plan,
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
        parts = raw_output.split("```")
        if len(parts) >= 2:
            raw_output = parts[1]
            if raw_output.startswith("python"):
                raw_output = raw_output[len("python"):]
        raw_output = raw_output.strip()

    validate_test_code(raw_output)

    return raw_output


if __name__ == "__main__":
    import os

    with open("artifacts/requirements.json", "r", encoding="utf-8") as f:
        reqs = json.load(f)
    with open("artifacts/plan.json", "r", encoding="utf-8") as f:
        plan = json.load(f)

    test_code = run_test_agent(reqs, plan)

    os.makedirs("generated", exist_ok=True)
    with open("generated/test_navigation_logic_generated.py", "w", encoding="utf-8") as f:
        f.write(test_code)

    print("Test code saved to generated/test_navigation_logic_generated.py")
