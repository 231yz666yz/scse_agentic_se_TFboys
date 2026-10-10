import importlib.util
import json
import os

## Create a function to run the simulation of the navigation logic.
## It should define a set of scenarios with different states (e.g., front_blocked, left_blocked, right_blocked), expected outputs (e.g., FORWARD, LEFT, RIGHT, STOP), and then run the decide_next_move function on each scenario.
## The function should collect the results, including whether the actual output matches the expected output, and return a report summarizing the results.
## The report must include the total number of scenarios, the number of passed and failed scenarios, and a success rate, which is the number of passed scenarios divided by the total number of scenarios.

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
NAV_LOGIC_PATH = os.path.join(PROJECT_DIR, "generated", "navigation_logic.py")
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "simulation_report.json")

VALID_ACTIONS = {"FORWARD", "LEFT", "RIGHT", "STOP"}


def make_state(
    goal_ahead=False,
    goal_on_left=False,
    goal_on_right=False,
    front_blocked=False,
    left_blocked=False,
    right_blocked=False,
):
    return {
        "goal_ahead": goal_ahead,
        "goal_on_left": goal_on_left,
        "goal_on_right": goal_on_right,
        "front_blocked": front_blocked,
        "left_blocked": left_blocked,
        "right_blocked": right_blocked,
    }


SCENARIOS = [
    (make_state(goal_ahead=True), "FORWARD", "goal ahead, all clear"),
    (make_state(goal_on_left=True), "LEFT", "goal on left, all clear"),
    (make_state(goal_on_right=True), "RIGHT", "goal on right, all clear"),
    (make_state(), "FORWARD", "no goal sensed, all clear -> default FORWARD"),

    (make_state(front_blocked=True), "LEFT", "front blocked, right clear -> default evade LEFT"),
    (make_state(front_blocked=True, left_blocked=True), "RIGHT", "front and left blocked, right clear -> RIGHT"),
    (make_state(front_blocked=True, right_blocked=True), "LEFT", "front and right blocked, left clear -> LEFT"),
    (make_state(front_blocked=True, left_blocked=True, right_blocked=True), "STOP",
     "all directions blocked, no safe direction -> STOP"),

    (make_state(goal_ahead=True, front_blocked=True), "LEFT",
     "front blocked dominates goal ahead -> default evade LEFT"),
    (make_state(goal_ahead=True, front_blocked=True, left_blocked=True), "RIGHT",
     "front and left blocked, right clear -> RIGHT"),
    (make_state(goal_ahead=True, front_blocked=True, right_blocked=True), "LEFT",
     "front and right blocked, left clear, goal ahead -> LEFT"),
    (make_state(goal_ahead=True, left_blocked=True), "FORWARD", "goal ahead, front clear; left block ignored"),
    (make_state(goal_ahead=True, right_blocked=True), "FORWARD", "goal ahead, front clear; right block ignored"),
    (make_state(goal_ahead=True, left_blocked=True, right_blocked=True), "FORWARD",
     "goal ahead, front clear; both sides blocked -> FORWARD"),

    (make_state(goal_on_left=True, right_blocked=True), "LEFT", "goal on left, left clear; right block ignored"),
    (make_state(goal_on_right=True, left_blocked=True), "RIGHT", "goal on right, right clear; left block ignored"),
    (make_state(goal_on_left=True, left_blocked=True), "RIGHT",
     "goal on left but blocked -> evade RIGHT (never turn into a block)"),
    (make_state(goal_on_right=True, right_blocked=True), "LEFT",
     "goal on right but blocked -> evade LEFT"),

    (make_state(goal_on_left=True, front_blocked=True), "LEFT",
     "front blocked with goal on left -> evade LEFT toward the goal side"),
    (make_state(goal_on_right=True, front_blocked=True), "RIGHT",
     "front blocked with goal on right -> evade RIGHT toward the goal side"),
    (make_state(goal_on_left=True, left_blocked=True, right_blocked=True), "FORWARD",
     "goal on left but both sides blocked, front clear -> FORWARD"),
]


def load_navigation_logic():
    spec = importlib.util.spec_from_file_location("navigation_logic", NAV_LOGIC_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.decide_next_move


def run_simulation():
    decide_next_move = load_navigation_logic()

    results = []
    passed_count = 0

    for state, expected, description in SCENARIOS:
        actual = decide_next_move(dict(state))
        valid_action = actual in VALID_ACTIONS
        scenario_passed = valid_action and actual == expected

        if scenario_passed:
            passed_count += 1

        results.append({
            "scenario": description,
            "state": state,
            "expected": expected,
            "actual": actual,
            "passed": scenario_passed,
        })

    total = len(SCENARIOS)
    failed_count = total - passed_count

    report = {
        "total_scenarios": total,
        "passed_scenarios": passed_count,
        "failed_scenarios": failed_count,
        "success_rate": passed_count / total if total > 0 else 0.0,
        "results": results,
    }

    return report


## If this script is run directly, run the simulation function and save the simulation report to a JSON file.
if __name__ == "__main__":
    report = run_simulation()

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Simulation finished: {report['passed_scenarios']}/{report['total_scenarios']} passed "
          f"(success rate: {report['success_rate']:.2%})")
    print(f"Report saved to {REPORT_PATH}")

    if report["failed_scenarios"] > 0:
        print("\nFailed scenarios:")
        for r in report["results"]:
            if not r["passed"]:
                print(f"  - [{r['scenario']}] expected {r['expected']}, got {r['actual']}")
