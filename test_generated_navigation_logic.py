import importlib.util
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
NAV_LOGIC_PATH = os.path.join(PROJECT_DIR, "generated", "navigation_logic.py")

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


TEST_CASES = [
    (make_state(goal_ahead=True), "FORWARD", "goal ahead, all clear (sample case)"),
    (make_state(goal_on_left=True), "LEFT", "goal on left, all clear"),
    (make_state(goal_on_right=True), "RIGHT", "goal on right, all clear"),
    (make_state(), "FORWARD", "no goal sensed, all clear -> default FORWARD"),

    (make_state(goal_ahead=True, front_blocked=True), "LEFT", "obstacle ahead overrides goal -> evade LEFT"),
    (make_state(front_blocked=True), "LEFT", "front blocked, sides clear -> evade LEFT"),
    (make_state(left_blocked=True), "FORWARD", "left blocked, front clear -> keep FORWARD"),
    (make_state(right_blocked=True), "FORWARD", "right blocked, front clear -> keep FORWARD"),

    (make_state(goal_ahead=True, left_blocked=True), "FORWARD", "goal ahead clear; left block ignored"),
    (make_state(goal_ahead=True, right_blocked=True), "FORWARD", "goal ahead clear; right block ignored"),
    (make_state(goal_on_left=True, right_blocked=True), "LEFT", "goal on left clear; right block ignored"),

    (make_state(goal_on_left=True, left_blocked=True), "FORWARD",
     "goal on left but blocked -> keep FORWARD while front is clear"),
    (make_state(goal_on_right=True, right_blocked=True), "FORWARD",
     "goal on right but blocked -> keep FORWARD while front is clear"),
    (make_state(goal_on_left=True, front_blocked=True), "LEFT",
     "goal on left but front blocked -> evade LEFT toward goal side"),

    (make_state(left_blocked=True, right_blocked=True), "FORWARD",
     "both sides blocked, front clear -> FORWARD"),
    (make_state(goal_on_left=True, left_blocked=True, right_blocked=True), "FORWARD",
     "goal blocked on left and right blocked, front clear -> FORWARD"),
    (make_state(front_blocked=True, left_blocked=True, right_blocked=True), "STOP",
     "all directions blocked, no safe move -> STOP"),
]


def load_navigation_logic():
    spec = importlib.util.spec_from_file_location("navigation_logic", NAV_LOGIC_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.decide_next_move


def test_navigation_logic():
    decide_next_move = load_navigation_logic()

    failures = []
    for state, expected, description in TEST_CASES:
        action = decide_next_move(dict(state))

        if action not in VALID_ACTIONS:
            failures.append(
                f"[{description}] returned invalid action {action!r} for state {state}"
            )
            continue

        if action != expected:
            failures.append(
                f"[{description}] expected {expected}, got {action} (state {state})"
            )

    if failures:
        report = "\n".join(failures)
        raise AssertionError(
            f"{len(failures)} of {len(TEST_CASES)} navigation cases failed:\n{report}"
        )

    print(f"All {len(TEST_CASES)} navigation logic cases PASSED")


if __name__ == "__main__":
    test_navigation_logic()
