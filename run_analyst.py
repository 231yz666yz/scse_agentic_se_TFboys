import json
import os

from agents.analyst_agent import run_analyst

BRIEF_PATH = "brief.txt"
OUTPUT_DIR = "artifacts"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "requirements.json")


def main():
    with open(BRIEF_PATH, "r", encoding="utf-8") as f:
        brief_text = f.read()

    requirements = run_analyst(brief_text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(requirements, f, indent=4, ensure_ascii=False)

    print(f"Validated requirements written to {OUTPUT_PATH}")
    print(json.dumps(requirements, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
