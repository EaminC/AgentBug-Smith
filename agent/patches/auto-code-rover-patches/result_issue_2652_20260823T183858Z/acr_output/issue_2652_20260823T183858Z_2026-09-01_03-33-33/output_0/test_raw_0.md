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


import sys

try:
    from strands.models.bedrock import BedrockModel
except ImportError as e:
    print(f"ERROR: Cannot import BedrockModel from strands.models.bedrock: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    m = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    try:
        # This should raise the intended TypeError, but if the bug is present,
        # next(iter({})) raises StopIteration instead.
        m._format_bedrock_messages([{"role": "user", "content": [{}]}])
    except StopIteration as e:
        # The bug is present: StopIteration bubbles up instead of intended TypeError.
        print_stacktrace(e)
        # Fail the script with an assertion error indicating the bug reproduces.
        raise AssertionError("Bug reproduced: bare StopIteration raised instead of TypeError") from e
    except TypeError:
        # Expected: TypeError raised, no bare StopIteration.
        pass
    else:
        # No exception raised: unexpected, fail.
        raise AssertionError("No exception raised for unsupported empty content block")


if __name__ == "__main__":
    main()
```
