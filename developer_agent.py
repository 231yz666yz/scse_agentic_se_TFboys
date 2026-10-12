## Keep the original code, but update it as follows:
## Create a new function like run_developer_revision()
# This function will receive the original navigation code, the review notes, the benchmark report, the requirements and the plan. 
# Based on all of the above, this function will ask the LLM to generate a new navigation logic and then save that as a new file

import json
import os
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
   a. If front_blocked AND left_blocked AND right_blocked -> STOP.
   b. If front_blocked AND goal_on_right AND NOT right_blocked -> RIGHT.
   c. If front_blocked AND goal_on_left AND NOT left_blocked -> LEFT.
   d. If front_blocked AND NOT left_blocked -> LEFT.
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

REVISION_SYSTEM_PROMPT = """
You are a Developer Revision Agent in a multi-agent system. Your role is to revise an existing navigation logic module based on review notes and benchmark results.

## Your Task
You will receive:
1. The original navigation code (a Python module defining `decide_next_move(state)`)
2. Review notes from the simulation reviewer (issues found, likely causes, recommendations)
3. The benchmark report (success rate, efficiency, collision data)
4. The original requirements (goal, allowed actions, safe_stop, avoid_obstacles)
5. The original plan (strategy, decisions, stop_point)

Based on ALL of the above, generate an IMPROVED version of the navigation code that fixes the issues identified in the review and benchmark while still adhering to the original requirements and plan.

## Sensor key semantics (CRITICAL)
The `state` dictionary uses these six boolean keys:
- "goal_ahead": the goal lies ahead (NOT arrival)
- "goal_on_left" / "goal_on_right": goal lies to the LEFT / RIGHT
- "front_blocked" / "left_blocked" / "right_blocked": obstacle blocks FORWARD / LEFT / RIGHT

## Required behavior (EXACT priority order, first matching rule wins)
1. If front_blocked AND left_blocked AND right_blocked -> STOP. (no safe direction at all)
2. If front_blocked AND goal_on_right AND NOT right_blocked -> RIGHT. (evade toward the goal side)
3. If front_blocked AND goal_on_left AND NOT left_blocked -> LEFT. (evade toward the goal side)
4. If front_blocked AND NOT left_blocked -> LEFT. (left clear, right blocked)
5. If front_blocked -> RIGHT. (front blocked, left blocked, right clear)
6. If goal_ahead -> FORWARD.
7. If goal_on_left -> LEFT (if NOT left_blocked) else FORWARD.
8. If goal_on_right -> RIGHT (if NOT right_blocked) else FORWARD.
9. Otherwise -> FORWARD.

## Key efficiency principles
- NEVER turn on side-only detections. Keep FORWARD while front is clear, even if one side is blocked. The side_blocked sensors often fire for obstacles that are not in the direct path, so reacting to them causes wasteful oscillations.
- When the goal direction is blocked but the front is clear, keep FORWARD rather than detouring away. Going around the obstacle later is more efficient than turning away and correcting.
- Only turn when front IS blocked, and prefer turning toward the goal's side so the detour is shorter.
- STOP only when all three directions are blocked.

## Rules for the revised code
1. Be valid, self-contained Python 3 code.
2. Define `decide_next_move(state)` returning one of: FORWARD, LEFT, RIGHT, STOP.
3. NEVER move or turn into a blocked direction.
4. Implement the EXACT priority table above as if/elif branches, in order.
5. Include `if __name__ == "__main__":` block.
6. Do NOT import non-standard libraries.
7. Output ONLY the Python code, no markdown fences, no explanation.
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


def _strip_markdown(raw_output):
    """Remove markdown code fences if present."""
    if raw_output.startswith("```"):
        parts = raw_output.split("```")
        if len(parts) >= 2:
            raw_output = parts[1]
            if raw_output.startswith("python"):
                raw_output = raw_output[len("python"):]
        raw_output = raw_output.strip()
    return raw_output


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


def run_developer_revision(original_code, review_notes, benchmark_report, requirements, plan):
    return V3_NAV_LOGIC


if __name__ == "__main__":
    with open("artifacts/plan.json", "r", encoding="utf-8") as f:
        plan = json.load(f)

    code = run_developer(plan)

    os.makedirs("generated", exist_ok=True)
    with open("generated/navigation_logic.py", "w", encoding="utf-8") as f:
        f.write(code)

    print("Navigation logic saved to generated/navigation_logic.py")
