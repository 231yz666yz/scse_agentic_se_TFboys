## Create a system prompt for the Reviewer Agent that instructs it to analyze the simulation report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that "needs_revision" is a boolean.



## Create a function to validate the output of the Reviewer Agent.
## It should check that the output is a JSON object with the required keys and that "needs_revision" is a boolean, and the rest of the keys are strings.


## Create a function to run the Reviewer Agent.
## It should take in the simulation report, send it to the Reviewer Agent, and return the validated output.