```python
def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    import sys
    try:
        from strands import Agent
        from strands.vended_plugins.skills import Skill, AgentSkills

        skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
        plugin = AgentSkills(skills=[skill])

        agent = Agent(
            system_prompt=[
                {"text": "Base instructions."},
                {"cachePoint": {"type": "default"}},
                {"text": "More instructions."},
            ],
            plugins=[plugin],
        )

        # Check initial _system_prompt_content
        initial = agent._system_prompt_content
        expected_initial = [
            {"text": "Base instructions."},
            {"cachePoint": {"type": "default"}},
            {"text": "More instructions."},
        ]
        assert initial == expected_initial, (
            f"Initial _system_prompt_content changed. Expected:\n{expected_initial}\nGot:\n{initial}"
        )

        # Run the agent to trigger _on_before_invocation hook in AgentSkills
        agent("hello")

        # Check that structured prompt is preserved (cachePoint present)
        after = agent._system_prompt_content
        # It should still have at least one dict with cachePoint key
        found_cache_point = any("cachePoint" in block for block in after)
        if not found_cache_point:
            raise AssertionError(
                f"Cache points lost after AgentSkills hook. _system_prompt_content:\n{after}"
            )

    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

    print("Test passed: Cache points preserved in _system_prompt_content after AgentSkills hook.")
    sys.exit(0)
```
