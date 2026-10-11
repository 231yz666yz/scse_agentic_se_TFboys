## the logic is similar to the run_planner and run_analyst files
import json
from pathlib import Path
from developer_agent import run_developer


def main():
    base_dir = Path(__file__).parent
    plan_file = base_dir / "artifacts" / "plan.json"
    output_file = base_dir / "navigation_logic.py"

    with open(plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)

    developer_code = run_developer(plan)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(developer_code)
        if not developer_code.endswith("\n"):
            f.write("\n")

    print(f"Developer code written to {output_file}")
    print("-" * 60)
    print(developer_code)


if __name__ == "__main__":
    main()
