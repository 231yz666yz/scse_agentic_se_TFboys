## The logic is fairly similar to the Analyst and Planner agents
import json
from ollama import chat

SYSTEM_PROMPT = """
You are a Developer Agent in a multi-agent system. Your role is to turn a navigation PLAN (produced by the Planner Agent) into runnable Python code that implements the robot's navigation logic.

## Your Task
Given a plan artifact, write a complete, self-contained Python module that implements the navigation strategy, decisions, and stop condition described in the plan. You must NOT question or change the plan; treat it as fixed requirements.

## Input
You will receive a JSON object with this structure:
{
  "strategy": "<textual strategy describing how the robot navigates>",
  "decisions": [
    "<a condition-action rule, e.g., 'If an obstacle is detected ahead, then STOP'>",
    ...
  ],
  "stop_point": "<the condition or location at which the robot must stop>"
}

## Sensor key semantics (CRITICAL)
The `state` dictionary uses these six boolean keys. Read these meanings exactly:
- "goal_ahead": the GOAL LIES AHEAD (in the forward direction). It does NOT mean the goal has been reached.
- "goal_on_left" / "goal_on_right": the goal lies to the LEFT / RIGHT. Again, NOT arrival.
- "front_blocked" / "left_blocked" / "right_blocked": an obstacle currently blocks the FORWARD / LEFT / RIGHT direction.
There is NO "goal reached" key in the state. Never return STOP just because a goal_* key is true: a visible goal is a direction to move TOWARD, not an arrival signal.

## Output Format
Respond with ONLY a single Python code block. No markdown fences, no explanation, no text before or after. The code must:

1. Be valid, self-contained Python 3 code that would compile without syntax errors.
2. Define a main entry point function named `decide_next_move(state)` that takes ONE argument: the sensor dictionary described above. It must return one action from the allowed actions: FORWARD, LEFT, RIGHT, STOP.
3. Define the allowed actions as module-level constants or an Enum.
4. Implement the plan's decisions as if/elif branches in `decide_next_move`, in this EXACT priority order (first matching rule wins):
   a. If front_blocked AND left_blocked AND right_blocked -> STOP. (only stop when no safe direction at all)
   b. If front_blocked AND goal_on_right AND NOT right_blocked -> RIGHT. (detour toward goal side)
   c. If front_blocked AND goal_on_left AND NOT left_blocked -> LEFT. (detour toward goal side)
   d. If front_blocked AND NOT left_blocked -> LEFT. (left clear, right blocked)
   e. If front_blocked -> RIGHT. (front blocked, left blocked, right clear)
   f. If goal_ahead -> FORWARD.
   g. If goal_on_left -> LEFT (if NOT left_blocked) else FORWARD.
   h. If goal_on_right -> RIGHT (if NOT right_blocked) else FORWARD.
   i. Otherwise -> FORWARD.
   KEY PRINCIPLES: (1) NEVER turn on side-only detections — keep FORWARD while front is clear, even if one side is blocked. (2) When goal direction is blocked but front is clear, keep FORWARD rather than detouring away. (3) Only turn when front IS blocked, and prefer turning toward the goal's side. (4) STOP only when all three directions are blocked.
5. The original navigation logic may be kept inside private helper functions, but external programs must call ONLY `decide_next_move(state)` and no other helper directly.
6. Be consistent with the `strategy` described in the plan.
7. Include a `if __name__ == "__main__":` block with a simple demo that calls `decide_next_move` with an example state dictionary.
8. Do NOT import libraries that are not part of the Python standard library.
9. Output ONLY the Python code. Do not wrap it in markdown or add any text before or after.

## Example skeleton (adapt to the actual plan)
class Action:
    FORWARD = "FORWARD"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STOP = "STOP"

def decide_next_move(state):
    if state["front_blocked"] and state["left_blocked"] and state["right_blocked"]:
        return Action.STOP
    if state["front_blocked"]:
        if state["goal_on_right"] and not state["right_blocked"]:
            return Action.RIGHT
        if state["goal_on_left"] and not state["left_blocked"]:
            return Action.LEFT
        if not state["left_blocked"]:
            return Action.LEFT
        return Action.RIGHT
    if state["goal_ahead"]:
        return Action.FORWARD
    if state["goal_on_left"]:
        return Action.LEFT if not state["left_blocked"] else Action.FORWARD
    if state["goal_on_right"]:
        return Action.RIGHT if not state["right_blocked"] else Action.FORWARD
    return Action.FORWARD

if __name__ == "__main__":
    print(decide_next_move({
        "goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
        "front_blocked": False, "left_blocked": False, "right_blocked": False,
    }))
"""

def validate_develope(data):
    if not isinstance(data, str):
        raise ValueError(f"Invalid type: expected str (Python code), got {type(data).__name__}")
    if not data.strip():
        raise ValueError("Code must not be empty")

    try:
        compile(data, filename="<navigation_logic>", mode="exec")
    except SyntaxError as e:
        raise ValueError(f"Code is not valid Python: {e}")

    if "def decide_next_move" not in data:
        raise ValueError("Code must define a function named `decide_next_move(state)`")

    required_actions = ["FORWARD", "LEFT", "RIGHT", "STOP"]
    missing_actions = [a for a in required_actions if a not in data]
    if missing_actions:
        raise ValueError(f"Code must define the allowed actions: missing {missing_actions}")

    if "__main__" not in data:
        raise ValueError("Code must include an `if __name__ == \"__main__\":` block")

    ns = {}
    exec(data, ns)
    fn = ns.get("decide_next_move")
    if not callable(fn):
        raise ValueError("decide_next_move must be callable")

    behavior_tests = [
        ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
          "front_blocked": True, "left_blocked": False, "right_blocked": False}, "LEFT",
         "front_blocked with sides clear must detour, not STOP"),
        ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
          "front_blocked": False, "left_blocked": True, "right_blocked": False}, "FORWARD",
         "left_blocked only with front clear must keep FORWARD"),
        ({"goal_ahead": False, "goal_on_left": False, "goal_on_right": False,
          "front_blocked": True, "left_blocked": True, "right_blocked": True}, "STOP",
         "all blocked must STOP"),
        ({"goal_ahead": False, "goal_on_left": True, "goal_on_right": False,
          "front_blocked": True, "left_blocked": False, "right_blocked": False}, "LEFT",
         "front_blocked with goal on left must detour LEFT"),
    ]
    for state, expected, label in behavior_tests:
        try:
            result = fn(state)
        except Exception as e:
            raise ValueError(f"Behavior test failed ({label}): {e}")
        if result != expected:
            raise ValueError(f"Behavior test failed ({label}): expected {expected}, got {result}")

    return True

V3_NAV_LOGIC = '''class Action:
    FORWARD = "FORWARD"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STOP = "STOP"

def decide_next_move(state):
    if state["front_blocked"] and state["left_blocked"] and state["right_blocked"]:
        return Action.STOP
    if state["front_blocked"]:
        if state["goal_on_right"] and not state["right_blocked"]:
            return Action.RIGHT
        if state["goal_on_left"] and not state["left_blocked"]:
            return Action.LEFT
        if not state["left_blocked"]:
            return Action.LEFT
        return Action.RIGHT
    if state["goal_ahead"]:
        return Action.FORWARD
    if state["goal_on_left"]:
        return Action.LEFT if not state["left_blocked"] else Action.FORWARD
    if state["goal_on_right"]:
        return Action.RIGHT if not state["right_blocked"] else Action.FORWARD
    return Action.FORWARD

if __name__ == "__main__":
    print(decide_next_move({
        "goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
        "front_blocked": False, "left_blocked": False, "right_blocked": False,
    }))
'''

def _strip_markdown(raw_output):
    if raw_output.startswith("```"):
        parts = raw_output.split("```")
        if len(parts) >= 2:
            raw_output = parts[1]
            if raw_output.startswith("python"):
                raw_output = raw_output[len("python"):]
        raw_output = raw_output.strip()
    return raw_output

def run_developer(plan):
    user_content = json.dumps(plan, ensure_ascii=False)

    response = chat(
        model="qwen3:8b",
        think=False,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw_output = response["message"]["content"].strip()
    raw_output = _strip_markdown(raw_output)

    try:
        validate_develope(raw_output)
        return raw_output
    except ValueError:
        print("[developer_agent] LLM output failed validation, falling back to V3_NAV_LOGIC")
        return V3_NAV_LOGIC
