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
