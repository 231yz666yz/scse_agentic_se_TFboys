import pytest
import importlib.util

# Load the module dynamically
spec = importlib.util.spec_from_file_location("navigation_logic", "generated/navigation_logic.py")
navigation_logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(navigation_logic)

def make_state(**kwargs):
    state = {
        "goal_ahead": False,
        "goal_on_left": False,
        "goal_on_right": False,
        "front_blocked": False,
        "left_blocked": False,
        "right_blocked": False
    }
    state.update(kwargs)
    return state

def test_decide_next_move():
    # Test scenario 1: Goal ahead, all clear -> FORWARD
    state = make_state(goal_ahead=True, front_blocked=False, left_blocked=False, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "FORWARD"

    # Test scenario 2: Goal on left, all clear -> LEFT
    state = make_state(goal_on_left=True, front_blocked=False, left_blocked=False, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "LEFT"

    # Test scenario 3: Goal on right, all clear -> RIGHT
    state = make_state(goal_on_right=True, front_blocked=False, left_blocked=False, right_blocked=False)
    assert navigation_logic.dec
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 4: No goal sensed, all clear -> FORWARD (default)
    state = make_state(front_blocked=False, left_blocked=False, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "FORWARD"

    # Test scenario 5: Front blocked, right clear -> RIGHT (evade, never freeze)
    state = make_state(front_blocked=True, right_blocked=False, left_blocked=False)
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 6: Front and left blocked, right clear -> RIGHT
    state = make_state(front_blocked=True, left_blocked=True, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 7: Front and right blocked, left clear -> LEFT
    state = make_state(front_blocked=True, right_blocked=True, left_blocked=False)
    assert navigation_logic.decide_next_move(state) == "LEFT"

    # Test scenario 8: All three directions blocked -> STOP (only STOP case)
    state = make_state(front_blocked=True, left_blocked=True, right_blocked=True)
    assert navigation_logic.decide_next_move(state) == "STOP"

    # Test scenario 9: Goal ahead, front blocked -> RIGHT (evasion dominates goal direction)
    state = make_state(goal_ahead=True, front_blocked=True, right_blocked=False, left_blocked=False)
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 10: Goal ahead, front clear, side blocked -> FORWARD
    state = make_state(goal_ahead=True, front_blocked=False, left_blocked=True, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "FORWARD"

    # Test scenario 11: Goal on left, left blocked -> RIGHT (never turn into blocked)
    state = make_state(goal_on_left=True, left_blocked=True, front_blocked=False, right_blocked=False)
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 12: Goal on right, right blocked -> LEFT
    state = make_state(goal_on_right=True, right_blocked=True, front_blocked=False, left_blocked=False)
    assert navigation_logic.decide_next_move(state) == "LEFT"

    # Test scenario 13: Goal on left, front blocked -> RIGHT
    state = make_state(goal_on_left=True, front_blocked=True, right_blocked=False, left_blocked=False)
    assert navigation_logic.decide_next_move(state) == "RIGHT"

    # Test scenario 14: Both sides blocked, front clear -> FORWARD
    state = make_state(front_blocked=False, left_blocked=True, right_blocked=True)
    assert navigation_logic.decide_next_move(state) == "FORWARD"

    # Test scenario 15: The function must always return one of FORWARD, LEFT, RIGHT, STOP
    state = make_state(goal_ahead=True, front_blocked=True, left_blocked=False, right_blocked=False)
    result = navigation_logic.decide_next_move(state)
    assert result in ["FORWARD", "LEFT", "RIGHT", "STOP"]

    # Test scenario for missing keys
    state = make_state(goal_ahead=True, front_blocked=True)
    result = navigation_logic.decide_next_move(state)
    assert result in ["FORWARD", "LEFT", "RIGHT", "STOP"]