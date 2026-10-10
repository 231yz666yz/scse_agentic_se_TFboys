import json
import subprocess
import ast

## Load the world files for the IR-SIM benchmark.

## Create a function to run the IR-SIM benchmark for a given world file.
## It should call the test_irsim_with_agent.py script with the world file as an argument, capture the output, and extract the report from the output.




## Create a main function to run the IR-SIM benchmark for all world files and generate a summary report.
## The summary report should include the total number of worlds, the number of worlds where the goal was reached, the success rate, the number of efficient worlds, the number of inefficient but successful worlds, the number of failed worlds, the efficiency rate, and the average steps taken across all worlds. The report should be saved to a JSON file.
## The benchmark report must have the following structure:
""" benchmark_report = {
        "total_worlds": total,
        "goals_reached": reached_goal_count,
        "success_rate": reached_goal_count / total,
        "efficient_worlds": efficient_count,
        "inefficient_success_worlds": inefficient_success_count,
        "failed_worlds": failed_count,
        "efficiency_rate": efficient_count / total,
        "average_steps_taken": average_steps,
        "results": results
    } """
## Save the benchmark report to a JSON file named "irsim_benchmark_report.json" under the artifacts folder, and print the report to the console in a readable format.
