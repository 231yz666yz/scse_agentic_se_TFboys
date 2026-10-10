import json
import logging
import os
import shutil
import subprocess
import sys

## Import all the necessary functions from other modules to run the entire pipeline.

from agents.analyst_agent import run_analyst
from agents.planner_agent import run_planner
from developer_agent import run_developer, run_developer_revision
from test_agent import run_test_agent
import runner
from reviewer_agent import run_reviewer
import benchmark_irsim
from reviewer_benchmark_agent import run_benchmark_reviewer

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
GENERATED_DIR = os.path.join(PROJECT_DIR, "generated")
BRIEF_PATH = os.path.join(PROJECT_DIR, "brief.txt")
TRACE_LOG_PATH = os.path.join(PROJECT_DIR, "trace.log")

REQUIREMENTS_PATH = os.path.join(ARTIFACTS_DIR, "requirements.json")
PLAN_PATH = os.path.join(ARTIFACTS_DIR, "plan.json")
NAV_LOGIC_PATH = os.path.join(GENERATED_DIR, "navigation_logic.py")
NAV_LOGIC_V1_PATH = os.path.join(GENERATED_DIR, "navigation_logic_v1.py")
NAV_LOGIC_V2_PATH = os.path.join(GENERATED_DIR, "navigation_logic_v2.py")
GENERATED_TESTS_PATH = os.path.join(GENERATED_DIR, "test_navigation_logic_generated.py")
SIM_REPORT_PATH = os.path.join(ARTIFACTS_DIR, "simulation_report.json")
SIM_REVIEW_PATH = os.path.join(ARTIFACTS_DIR, "simulation_review.json")
BENCH_REVIEW_PATH = os.path.join(ARTIFACTS_DIR, "benchmark_review.json")


## It should create necessary directories, or check that it exists.

def ensure_directories():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(GENERATED_DIR, exist_ok=True)


## Setup logging: everything is recorded in trace.log.

logging.basicConfig(
    filename=TRACE_LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="w",
)
logger = logging.getLogger("pipeline")
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
logger.addHandler(_console)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_brief():
    with open(BRIEF_PATH, "r", encoding="utf-8") as f:
        brief = f.read()
    logger.info("Orchestrator loaded brief.txt (%d characters)", len(brief))
    return brief


def run_generated_tests():
    """Run the Test Agent's generated pytest file and log the outcome."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", GENERATED_TESTS_PATH, "-q"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        tail = (result.stdout or "").strip().splitlines()[-5:]
        logger.info("Test Agent generated tests finished with return code %s", result.returncode)
        for line in tail:
            logger.info("pytest: %s", line)
    except FileNotFoundError:
        logger.warning("pytest is not installed; skipping generated test execution")


## Write a main function to run the entire pipeline.
## Then run each agent in sequence, save their outputs to files, and log events.
## Logging events should include the name of the agent and the action taken,
## such as "Analyst Agent created requirements.json".

def run_pipeline():
    logger.info("=== Pipeline started ===")
    ensure_directories()

    # 1. Load the brief
    brief = load_brief()

    # 2. Run the Analyst agent
    logger.info("Running Analyst Agent...")
    requirements = run_analyst(brief)
    save_json(REQUIREMENTS_PATH, requirements)
    logger.info("Analyst Agent created requirements.json")

    # 3. Run the Planner agent
    logger.info("Running Planner Agent...")
    plan = run_planner(requirements)
    save_json(PLAN_PATH, plan)
    logger.info("Planner Agent created plan.json")

    # 4. Run the Developer agent
    logger.info("Running Developer Agent...")
    navigation_code = run_developer(plan)
    with open(NAV_LOGIC_PATH, "w", encoding="utf-8") as f:
        f.write(navigation_code)
    logger.info("Developer Agent created generated/navigation_logic.py")

    # 5. Run the Test agent
    logger.info("Running Test Agent...")
    test_code = run_test_agent(requirements, plan)
    with open(GENERATED_TESTS_PATH, "w", encoding="utf-8") as f:
        f.write(test_code)
    logger.info("Test Agent created generated/test_navigation_logic_generated.py")
    run_generated_tests()

    # 6. Run the simulation
    logger.info("Running Simulation Runner...")
    simulation_report = runner.run_simulation()
    save_json(SIM_REPORT_PATH, simulation_report)
    logger.info(
        "Simulation Runner created simulation_report.json (%d/%d scenarios passed)",
        simulation_report["passed_scenarios"],
        simulation_report["total_scenarios"],
    )

    # 7. Run the reviewer agent
    logger.info("Running Reviewer Agent...")
    simulation_review = run_reviewer(simulation_report)
    save_json(SIM_REVIEW_PATH, simulation_review)
    logger.info("Reviewer Agent created simulation_review.json (needs_revision=%s)",
                simulation_review["needs_revision"])

    # 8. Run the IR-SIM benchmark
    logger.info("Running IR-SIM benchmark (this runs all four worlds)...")
    benchmark_report = benchmark_irsim.main()
    logger.info("IR-SIM benchmark created artifacts/irsim_benchmark_report.json")

    # 9. Run the benchmark reviewer
    logger.info("Running Benchmark Reviewer Agent...")
    benchmark_review = run_benchmark_reviewer(benchmark_report)
    save_json(BENCH_REVIEW_PATH, benchmark_review)
    logger.info("Benchmark Reviewer Agent created benchmark_review.json (needs_revision=%s)",
                benchmark_review["needs_revision"])

    # 10. Revision: if any review requests it, revise the navigation logic and re-run everything
    if simulation_review.get("needs_revision") or benchmark_review.get("needs_revision"):
        logger.info("Revision required -> running Developer Revision...")
        revised_code = run_developer_revision(
            navigation_code, simulation_review, benchmark_report, requirements, plan
        )

        # Keep the original as v1, save the revision as a new file (v2),
        # and make it the active logic so all downstream tools use it.
        shutil.copyfile(NAV_LOGIC_PATH, NAV_LOGIC_V1_PATH)
        with open(NAV_LOGIC_V2_PATH, "w", encoding="utf-8") as f:
            f.write(revised_code)
        with open(NAV_LOGIC_PATH, "w", encoding="utf-8") as f:
            f.write(revised_code)
        logger.info("Developer Agent created generated/navigation_logic_v2.py "
                    "(original kept as generated/navigation_logic_v1.py)")

        # Re-run the simulation
        logger.info("Re-running Simulation Runner on revised logic...")
        simulation_report = runner.run_simulation()
        save_json(SIM_REPORT_PATH, simulation_report)
        logger.info(
            "Simulation Runner re-created simulation_report.json (%d/%d scenarios passed)",
            simulation_report["passed_scenarios"],
            simulation_report["total_scenarios"],
        )
        simulation_review = run_reviewer(simulation_report)
        save_json(SIM_REVIEW_PATH, simulation_review)
        logger.info("Reviewer Agent re-created simulation_review.json (needs_revision=%s)",
                    simulation_review["needs_revision"])

        # Re-run the IR-SIM benchmark
        logger.info("Re-running IR-SIM benchmark on revised logic...")
        benchmark_report = benchmark_irsim.main()
        logger.info("IR-SIM benchmark re-created artifacts/irsim_benchmark_report.json")

        # Re-run the benchmark reviewer
        benchmark_review = run_benchmark_reviewer(benchmark_report)
        save_json(BENCH_REVIEW_PATH, benchmark_review)
        logger.info("Benchmark Reviewer Agent re-created benchmark_review.json (needs_revision=%s)",
                    benchmark_review["needs_revision"])
    else:
        logger.info("No revision required by either reviewer.")

    logger.info("=== Pipeline finished successfully ===")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception:
        logger.exception("Pipeline failed")
        raise
