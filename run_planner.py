import json
from pathlib import Path
from agents.planner_agent import run_planner


## Create a function/logic that reads the requirements from requirements.json,
# then calls the run_planner function with the requirements as input, and finally writes the validated plan to plan.json.
def main():
    base_dir = Path(__file__).parent
    artifacts_dir = base_dir / "artifacts"
    requirements_path = artifacts_dir / "requirements.json"
    plan_path = artifacts_dir / "plan.json"

    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = json.load(f)

    plan = run_planner(requirements)

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)

    print(f"Plan written to {plan_path}")
    print(json.dumps(plan, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
