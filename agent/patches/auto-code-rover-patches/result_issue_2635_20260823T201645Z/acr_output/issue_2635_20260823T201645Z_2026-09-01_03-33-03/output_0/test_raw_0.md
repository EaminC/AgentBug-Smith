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
    from strands.models.model import _estimate_tokens_with_heuristic
except ImportError as e:
    print("Failed to import _estimate_tokens_with_heuristic from strands.models.model:", file=sys.stderr)
    print(e, file=sys.stderr)
    sys.exit(1)

def main():
    messages = [{
        "role": "user",
        "content": [{
            "toolResult": {
                "status": "success",
                "content": [{"json": {"x": "lorem ipsum " * 1000}}],
            }
        }]
    }]

    try:
        tokens = _estimate_tokens_with_heuristic(messages)
        assert tokens > 0, "Token count is 0 - likely missing json counting in toolResult content"
    except AssertionError as e:
        print_stacktrace(e)
        raise

if __name__ == "__main__":
    main()
```
