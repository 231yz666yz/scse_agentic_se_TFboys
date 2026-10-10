

## Create a system prompt for the Reviewer Agent that instructs it to analyze the IR-SIM Benchmark report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans.



## Create a function to validate the output of the Reviewer Agent for the benchmark report.
## It should check that the output is a JSON object with the required keys and that "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans, and the rest of the keys are strings.
## If the output does not meet these criteria, raise a ValueError.





## Create a function to build a deterministic review from the benchmark report.
## This function analyzes the benchmark report and determines the values for "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" based on the measured benchmark fields.
## It returns a dictionary with the keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## If the benchmark report does not contain the required fields, default values will be used.
## If safety_passed is false, the issue will be described as "Unsafe benchmark behavior detected". Safety is measured as any world having collision_or_done true while reached_goal is false.
## If goal_completion_passed is false, the issue will be described as "Goal completion failure". Goal completion is measured as success_rate being less than 1.0.
## If efficiency_passed is false, the issue will be described as "Successful but inefficient navigation". Efficiency is measured as inefficient_success_worlds being greater than 0 or efficiency_rate being less than 1.0.





## Create a function to run the Reviewer Agent for the benchmark report.
## It should take in the benchmark report, build a deterministic review, send both to the Reviewer Agent, and return the validated output.
## The deterministic review is used to ensure that the pass/fail booleans in the output are based on the measured benchmark results, even if the LLM phrases the issue, likely cause, and recommendation.
## The output of this function will be a dictionary with the keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
