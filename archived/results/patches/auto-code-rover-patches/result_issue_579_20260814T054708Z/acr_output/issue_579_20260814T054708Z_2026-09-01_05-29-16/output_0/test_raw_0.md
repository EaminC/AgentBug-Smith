```python
# reproducer.py
from strands import Agent
from strands.tools import tool

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


@tool
def teacher(query: str, **kwargs):
    hidden_number = kwargs.get("hidden_number")
    agent = kwargs.get("agent")
    # This will fail if agent is None
    assert agent is not None, "Agent information is not passed to sub-agent tool"
    print(f"Getting query from {agent.name}")

    teacher_agent = Agent(
        name="teacher",
        system_prompt=f"You're a math teacher help with math problems. You have got an hidden number {hidden_number} and you must use it in the calculation"
    )

    return teacher_agent(query)

def main():
    try:
        coordinator = Agent(
            name="coordinator",
            system_prompt="You're a coordinator, always pass your query to teacher agent",
            tools=[teacher]
        )
        invocation_state = {"hidden_number": 3}
        response = coordinator("times 2", **invocation_state)
        # If no AssertionError, print success and exit 0
        print("Invocation state passed correctly. Test passed.")
    except Exception as e:
        print_stacktrace(e)
        # Raise AssertionError to indicate the issue presence
        raise AssertionError("Invocation state was not passed correctly to sub-agent tool.") from e

if __name__ == "__main__":
    main()
```
