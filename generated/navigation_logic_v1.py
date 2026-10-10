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