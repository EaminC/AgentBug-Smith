```python
# reproducer.py
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

    from strands import Agent
    from strands.models.litellm import LiteLLMModel
    from strands.types.exceptions import ContextWindowOverflowException

    model = LiteLLMModel(
        model_id="litellm_proxy/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        params={
            "api_base": "http://0.0.0.0:4000",
            "api_key": "key",
        },
    )
    agent = Agent(model=model)
    long_input = "Hi" * 1000000

    try:
        agent(long_input)
        # If no exception or different exception, means issue is fixed
        print("No ContextWindowOverflowException was raised, issue fixed.")
        sys.exit(0)
    except ContextWindowOverflowException as e:
        # Proper expected behavior, exit 0
        print("Caught expected ContextWindowOverflowException, issue fixed.")
        sys.exit(0)
    except Exception as e:
        # Unexpected exception means issue is present
        print_stacktrace(e)
        raise AssertionError(
            "Did not catch ContextWindowOverflowException, got different exception instead."
        )
```
