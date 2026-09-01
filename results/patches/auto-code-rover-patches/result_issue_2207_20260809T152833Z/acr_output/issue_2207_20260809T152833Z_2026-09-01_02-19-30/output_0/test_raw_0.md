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
    try:
        from agentscope.model import ChatResponse, FinishedReason

        # Construct a ChatResponse with finished_reason=INTERRUPTED
        r = ChatResponse(
            content=[],
            is_last=True,
            finished_reason=FinishedReason.INTERRUPTED,
        )

        # The issue: dict access returns INTERRUPTED, attribute returns COMPLETED
        if r["finished_reason"] != FinishedReason.INTERRUPTED:
            raise AssertionError(
                f"Dict access finished_reason expected INTERRUPTED but got {r['finished_reason']}"
            )
        if r.finished_reason != FinishedReason.INTERRUPTED:
            raise AssertionError(
                f"Attribute access finished_reason expected INTERRUPTED but got {r.finished_reason}"
            )

    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

    # Exit with code 0 if no assertion raised => issue fixed
    sys.exit(0)
```
