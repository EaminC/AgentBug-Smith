```
<file>gpt_engineer/steps.py</file>
<original>def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    messages = [
</original>
<patched>def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    # The clarifications are appended as separate messages, but if they contain
    # instructions forbidding python or requesting another language, this function
    # should inject that correctly into the user prompt or system prompt so the model
    # respects it.
    # Patch: concatenate clarifications properly into the prompt with emphasis, e.g.
    # by merging clarifications text into the user message, instead of separately,
    # so model "understands" the constraints.
    clarifications_combined = "\n".join(dbs.load("clarifications") or [])
    base_prompt = dbs.load("prompt") or ""

    # Emphasize clarifications especially forbidding python
    if clarifications_combined.strip():
        full_prompt = f"{base_prompt}\n\nIMPORTANT CLARIFICATIONS:\n{clarifications_combined}"
    else:
        full_prompt = base_prompt

    messages = [
        SystemMessage(content=dbs.load("system_prompt") or ""),
        HumanMessage(content=full_prompt),
    ]
</patched>
```