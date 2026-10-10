## The logic is fairly similar to the Analyst and Planner agents
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
2. If front_blocked AND NOT right_blocked -> RIGHT. (front is blocked, right side is clear -> evade RIGHT)
3. If front_blocked AND NOT left_blocked -> LEFT. (front and right are blocked, left is clear -> evade LEFT)
4. If goal_ahead -> FORWARD.
5. If goal_on_left AND NOT left_blocked -> LEFT.
6. If goal_on_right AND NOT right_blocked -> RIGHT.
7. If left_blocked AND NOT right_blocked -> RIGHT.
8. If right_blocked AND NOT left_blocked -> LEFT.
9. Otherwise -> FORWARD.

## CRITICAL semantics for STOP (most common revision mistake)
Do NOT return STOP merely because the front is blocked. STOP is ONLY correct when
front, left AND right are ALL blocked (no safe direction exists). When the front is
blocked but any side is clear, the robot MUST turn to the clear side and move around
the obstacle. A robot that stops on front_blocked alone freezes forever in simulation
and fails every benchmark world.

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

    validate_develope(raw_output)

    return raw_output


def run_developer_revision(original_code, review_notes, benchmark_report, requirements, plan):
    """Ask the LLM to generate a revised navigation logic based on all feedback.

    Parameters
    ----------
    original_code : str
        The original navigation logic Python source.
    review_notes : dict
        The reviewer agent's output (issue, likely_cause, recommendation, needs_revision).
    benchmark_report : dict
        The IR-SIM benchmark report.
    requirements : dict
        The requirements artifact from the analyst.
    plan : dict
        The plan artifact from the planner.

    Returns
    -------
    str
        Validated Python source code for the revised navigation logic.
    """
    user_content = json.dumps({
        "original_code": original_code,
        "review_notes": review_notes,
        "benchmark_report": benchmark_report,
        "requirements": requirements,
        "plan": plan,
    }, ensure_ascii=False)

    response = chat(
        model="qwen3:8b",
        think=False,
        messages=[
            {"role": "system", "content": REVISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw_output = response["message"]["content"].strip()
    raw_output = _strip_markdown(raw_output)

    validate_develope(raw_output)

    return raw_output


if __name__ == "__main__":
    with open("artifacts/plan.json", "r", encoding="utf-8") as f:
        plan = json.load(f)

    code = run_developer(plan)

    os.makedirs("generated", exist_ok=True)
    with open("generated/navigation_logic.py", "w", encoding="utf-8") as f:
        f.write(code)

    print("Navigation logic saved to generated/navigation_logic.py")
