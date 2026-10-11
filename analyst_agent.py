import json

import ollama

MODEL = "qwen3:8b"

REQUIRED_KEYS = {"goal", "allowed_actions", "safe_stop", "avoid_obstacles"}

VALID_ACTIONS = {"FORWARD", "LEFT", "RIGHT", "STOP"}

SYSTEM_PROMPT = """You are a requirements analyst (requirements engineer) for a mobile robot navigation system.

YOUR TASK:
Read the human-written brief given to you and extract from it one single, explicit set of software requirements.

CONSTRAINTS AND RULES:
- Use ONLY the information contained in the brief. Do not invent features, use cases or success criteria that the brief does not mention.
- The goal must describe the navigation objective stated in the brief, as a string.
- The only valid robot actions are exactly: FORWARD, LEFT, RIGHT, STOP. Never invent any other action.
- "safe_stop" must be true if the brief says the robot must stop when it cannot move anywhere, otherwise false.
- "avoid_obstacles" must be true if the brief says the robot must never move into a blocked direction, otherwise false.
- The two boolean values must be JSON booleans (true/false), not strings.
- Output ONLY the JSON object. No markdown code fences, no comments, no explanation before or after it.

OUTPUT STRUCTURE (exactly these keys, no more, no less):
{
    "goal": "<the navigation objective, as a string>",
    "allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
    "safe_stop": <true or false>,
    "avoid_obstacles": <true or false>
}"""


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def validate_requirements(result):
    if not isinstance(result, dict):
        raise ValueError(f"Expected a dict, got {type(result).__name__}")

    keys = set(result.keys())
    missing = REQUIRED_KEYS - keys
    extra = keys - REQUIRED_KEYS

    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    
    if extra:
        raise ValueError(f"Unexpected extra keys: {sorted(extra)}")

    if not isinstance(result["goal"], str):
        raise ValueError(f"'goal' must be a string, got {type(result['goal']).__name__}")
    
    if not isinstance(result["allowed_actions"], list):
        raise ValueError(
            f"'allowed_actions' must be a list, got {type(result['allowed_actions']).__name__}"
        )
    
    if not isinstance(result["safe_stop"], bool):
        raise ValueError(f"'safe_stop' must be a boolean, got {type(result['safe_stop']).__name__}")
    
    if not isinstance(result["avoid_obstacles"], bool):
        raise ValueError(
            f"'avoid_obstacles' must be a boolean, got {type(result['avoid_obstacles']).__name__}"
        )

    for action in result["allowed_actions"]:
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action {action!r}; allowed: {sorted(VALID_ACTIONS)}")

    return True


def run_analyst(brief_text):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system", 
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user", 
                "content": brief_text
            },
        ],
    )
    raw = response["message"]["content"]

    json_text = extract_json(raw)
    try:
        requirements = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Qwen did not return valid JSON ({e}). Raw reply was:\n{raw}")

    validate_requirements(requirements)
    return requirements


if __name__ == "__main__":
    with open("brief.txt", "r", encoding="utf-8") as f:
        brief = f.read()

    reqs = run_analyst(brief)
    print(json.dumps(reqs, indent=4))
