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
    # Combine main prompt with clarifications, ensuring clarifications are included explicitly
    # and that restrictions on language (e.g., forbidding python) are respected by prompting.
    clarifications = dbs.clarifications.read()
    main_prompt = dbs.prompt.read()

    # Construct combined user content by joining main prompt and clarifications explicitly
    user_content = main_prompt.strip()
    if clarifications.strip():
        user_content += "\n\nClarifications:\n" + clarifications.strip()

    # Add explicit instructions to the prompt to forbid Python if clarifications mention it
    # This helps the AI better understand the language restrictions.
    if "forbid python" in clarifications.lower() or "no python" in clarifications.lower():
        user_content += (
            "\n\nImportant: Do NOT use Python or any Python code in your response. "
            "Use the languages specified in the clarifications."
        )

    messages = [
</patched>
```

```
<file>gpt_engineer/steps.py</file>
<original>def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    messages = [
        SystemMessage(content=dbs.system_spec.read()),
        HumanMessage(content=dbs.prompt.read()),
    ]
    messages = ai.start(
        system=dbs.system_spec.read(),
        user=dbs.prompt.read(),
        step_name="gen_spec",
    )
    messages = ai.next(messages, step_name="gen_spec")
    dbs.spec.write(messages[-1].content)
    return messages
</original>
<patched>def gen_spec(ai: AI, dbs: DBs) -> List[Message]:
    """
    Generate a spec from the main prompt + clarifications and save the results to
    the workspace
    """
    # Compose the system message once to avoid redundant calls.
    system_content = dbs.system_spec.read()

    # Use the combined user content string built above.
    clarifications = dbs.clarifications.read()
    main_prompt = dbs.prompt.read()

    user_content = main_prompt.strip()
    if clarifications.strip():
        user_content += "\n\nClarifications:\n" + clarifications.strip()

    # Include explicit language forbidding instructions if noted in clarifications
    if "forbid python" in clarifications.lower() or "no python" in clarifications.lower():
        user_content += (
            "\n\nImportant: Do NOT use Python or any Python code in your response. "
            "Use only the languages specified in the clarifications."
        )

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    messages = ai.start(
        system=system_content,
        user=user_content,
        step_name="gen_spec",
    )
    messages = ai.next(messages, step_name="gen_spec")
    dbs.spec.write(messages[-1].content)
    return messages
</patched>
```

# Explanation:

# The key to fixing the issue lies in ensuring that any clarifications or instructions to forbid Python are properly integrated into the user prompt sent to the AI. The original code only read and passed the prompt separately without explicitly incorporating clarifications or additional instructions.

# In the patch, clarifications are read and concatenated explicitly with the main prompt, under a "Clarifications:" heading. Additionally, if the clarifications contain phrases like "forbid python" or "no python", we append explicit instructions forbidding Python code to bolster the AI understanding.

# This change should ensure the AI prompt respects and follows language restrictions, fixing the bug where the AI always outputs Python code despite requests otherwise. Other existing functionality and flow is preserved.