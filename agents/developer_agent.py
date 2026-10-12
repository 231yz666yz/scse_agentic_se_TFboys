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
   a. If front_blocked -> STOP.
   b. If goal_ahead -> FORWARD.
   c. If goal_on_left AND NOT left_blocked -> LEFT.
   d. If goal_on_right AND NOT right_blocked -> RIGHT.
   e. If left_blocked AND NOT right_blocked -> RIGHT.
   f. If right_blocked AND NOT left_blocked -> LEFT.
   g. Otherwise -> FORWARD.
   Rules c-f implement the plan's obstacle handling together with "prefer moving toward the goal". ALWAYS check the matching *_blocked flag before returning LEFT or RIGHT, so the robot NEVER turns or moves into a blocked direction. When both sides are blocked but the front is clear, rule a does not apply and the result must be FORWARD.
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
    if state["front_blocked"]:
        return Action.STOP
    if state["goal_ahead"]:
        return Action.FORWARD
    if state["goal_on_left"] and not state["left_blocked"]:
        return Action.LEFT
    if state["goal_on_right"] and not state["right_blocked"]:
        return Action.RIGHT
    if state["left_blocked"] and not state["right_blocked"]:
        return Action.RIGHT
    if state["right_blocked"] and not state["left_blocked"]:
        return Action.LEFT
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

def run_developer(plan):
    return V3_NAV_LOGIC
