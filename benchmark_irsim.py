import json
import os
import subprocess
import sys

## Load the world files for the IR-SIM benchmark.

## Create a function to run the IR-SIM benchmark for a given world file.
## It should call the test_irsim_with_agent.py script with the world file as an argument,
## capture the output, and extract the report from the output.

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_SCRIPT = os.path.join(PROJECT_DIR, "test_irsim_with_agent.py")
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "irsim_report.json")
BENCHMARK_REPORT_PATH = os.path.join(ARTIFACTS_DIR, "irsim_benchmark_report.json")

WORLD_FILES = [
    "irsim_worlds/world_easy.yaml",
    "irsim_worlds/world_medium.yaml",
    "irsim_worlds/world_hard.yaml",
    "irsim_worlds/world_custom.yaml",
]


def run_irsim_benchmark(world_file):
    """Run test_irsim_with_agent.py for one world and extract its report.

    The test script writes artifacts/irsim_report.json at the end of its run,
    so we read that file after the subprocess finishes. MPLBACKEND=Agg keeps
    matplotlib offscreen so plt.show() does not block the automation
    (the test script itself is not modified).
    """
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"

    try:
        subprocess.run(
            [sys.executable, TEST_SCRIPT, world_file],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print(f"WARNING: {world_file} timed out after 600s")

    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
    else:
        report = {
            "reached_goal": False,
            "collision_or_done": True,
            "steps_taken": 0,
            "max_steps_allowed": 300,
            "efficient_step_limit": 200,
            "efficiency_status": "failed",
            "efficiency_passed": False,
            "final_pose": None,
            "history_length": 0,
        }

    report["world_file"] = world_file
    return report


## Create a main function to run the IR-SIM benchmark for all world files and generate a summary report.
## The summary report should include the total number of worlds, the number of worlds where the goal
## was reached, the success rate, the number of efficient worlds, the number of inefficient but
## successful worlds, the number of failed worlds, the efficiency rate, and the average steps taken
## across all worlds. The report should be saved to a JSON file.

def main():
    results = []

    for world_file in WORLD_FILES:
        print(f"\n=== Running IR-SIM benchmark for {world_file} ===")
        report = run_irsim_benchmark(world_file)
        results.append(report)
        print(f"Result: reached_goal={report.get('reached_goal')}, "
              f"steps_taken={report.get('steps_taken')}, "
              f"efficiency_status={report.get('efficiency_status')}")

    total = len(results)
    reached_goal_count = sum(1 for r in results if r.get("reached_goal") is True)
    efficient_count = sum(1 for r in results if r.get("efficiency_status") == "efficient")
    inefficient_success_count = sum(
        1 for r in results if r.get("efficiency_status") == "acceptable_but_inefficient"
    )
    failed_count = sum(1 for r in results if r.get("reached_goal") is not True)
    total_steps = sum(r.get("steps_taken", 0) for r in results)
    average_steps = total_steps / total if total > 0 else 0.0

    benchmark_report = {
        "total_worlds": total,
        "goals_reached": reached_goal_count,
        "success_rate": reached_goal_count / total,
        "efficient_worlds": efficient_count,
        "inefficient_success_worlds": inefficient_success_count,
        "failed_worlds": failed_count,
        "efficiency_rate": efficient_count / total,
        "average_steps_taken": average_steps,
        "results": results,
    }

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(BENCHMARK_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2)

    ## Print the report to the console in a readable format.
    print("\n" + "=" * 60)
    print("IR-SIM BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total worlds:                   {benchmark_report['total_worlds']}")
    print(f"Goals reached:                  {benchmark_report['goals_reached']}")
    print(f"Success rate:                   {benchmark_report['success_rate']:.2%}")
    print(f"Efficient worlds:               {benchmark_report['efficient_worlds']}")
    print(f"Inefficient but successful:     {benchmark_report['inefficient_success_worlds']}")
    print(f"Failed worlds:                  {benchmark_report['failed_worlds']}")
    print(f"Efficiency rate:                {benchmark_report['efficiency_rate']:.2%}")
    print(f"Average steps taken:            {benchmark_report['average_steps_taken']:.1f}")
    print("=" * 60)
    print(f"Report saved to {BENCHMARK_REPORT_PATH}")

    return benchmark_report


if __name__ == "__main__":
    main()
