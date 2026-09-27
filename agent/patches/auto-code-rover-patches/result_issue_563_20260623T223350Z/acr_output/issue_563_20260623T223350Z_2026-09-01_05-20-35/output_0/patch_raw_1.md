```
<file>gpt_engineer/steps.py</file>
<original> 
def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    messages = [
</original>
<patched> 
def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    # Combine the main prompt with clarifications ensuring forbidding python is respected
    clarifications = dbs.read("clarify/clarifications.txt")
    combined_prompt = dbs.read("prompt.txt")
    if clarifications:
        # Append clarifications explicitly to the prompt
        combined_prompt += "\n\nClarifications:\n" + clarifications
    
    # Inject explicit instruction to avoid Python if specified in clarifications or prompt
    # This helps ensure the model respects "no Python" instructions
    if "no python" in combined_prompt.lower() or "forbid python" in combined_prompt.lower():
        combined_prompt += "\n\nPlease DO NOT use Python in the generated code. Use the requested language exclusively."

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=combined_prompt),
    ]
</patched>
```
