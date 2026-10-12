import pytest
import importlib.util

# Load the module dynamically
spec = importlib.util.spec_from_file_location("navigation_logic", "generated/navigation_logic.py")
navigation_logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(navigation_logic)

def make_state(**kwargs):
    return {
        "goal_ahead": kwargs.get("goal_ahead", False),
        "goal_on_left": kwargs.get("goal_on_left", False),
        "goal_on_right": kwargs.get("goal_on_right", False),
        "front_blocked": kwargs.get("front_blocked", False),
        "left_blocked": kwargs.get("left_blocked", False),
        "right_blocked": kwargs.get("right_blocked", False),
    }

def test_decide_next_move():
    for scenario, expected in [
        # Scenario 1: Goal ahead, all clear
        ({"goal_ahead": True}, "FORWARD"),
        # Scenario 2: Goal on left, all clear
        ({"goal_on_left": True}, "LEFT"),
        # Scenario 3: Goal on right, all clear
        ({"goal_on_right": True}, "RIGHT"),
        # Scenario 4: No goal sensed, all clear
        ({}, "FORWARD"),
        # Scenario 5: Front blocked, sides clear
        ({"front_blocked": True}, "LEFT"),
        # Scenario 6: Front and left blocked, right clear
        ({"front_blocked": True, "left_blocked": True, "right_blocked": False}, "RIGHT"),
        # Scenario 7: Front and right blocked, left clear
        ({"front_blocked": True, "right_blocked": True, "left_blocked": False}, "LEFT"),
        # Scenario 8: All three directions blocked
        ({"front_blocked": True, "left_blocked": True, "right_blocked": True}, "STOP"),
        # Scenario 9: Goal ahead, front blocked
        ({"goal_ahead": True, "front_blocked": True}, "LEFT"),
        # Scenario 10: Goal ahead, front clear, side blocked
        ({"goal_ahead": True, "right_blocked": True}, "FORWARD"),
        # Scenario 11: Goal on left, left blocked
        ({"goal_on_left": True, "left_blocked": True}, "FORWARD"),
        # Scenario 12: Goal on right, right blocked
        ({"goal_on_right": True, "right_blocked": True}, "FORWARD"),
        # Scenario 13: Goal on left, front blocked
        ({"goal_on_left": True, "front_blocked": True}, "LEFT"),
        # Scenario 14: Goal on right, front blocked
        ({"goal_on_right": True, "front_blocked": True}, "RIGHT"),
        # Scenario 15: Both sides blocked, front clear
        ({"left_blocked": True, "right_blocked": True}, "FORWARD"),
        # Scenario 16: Left blocked only, front clear
        ({"left_blocked": True}, "FORWARD"),
        # Scenario 17: Right blocked only, front clear
        ({"right_blocked": True}, "FORWARD"),
    ]:
        state = make_state(**scenario)
        result = navigation_logic.decide_next_move(state)
        assert result in ["FORWARD", "LEFT", "RIGHT", "STOP"], f"Unexpected result: {result}"
        assert result == expected, f"Expected {expected}, got {result}"

def test_missing_keys():
    state = make_state()
    result = navigation_logic.decide_next_move(state)
    assert result == "FORWARD", f"Expected 'FORWARD', got {result}"