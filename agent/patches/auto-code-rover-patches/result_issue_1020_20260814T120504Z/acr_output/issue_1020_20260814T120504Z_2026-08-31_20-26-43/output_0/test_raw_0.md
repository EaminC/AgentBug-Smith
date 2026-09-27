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
    from strands import tool, ToolContext

    @tool(context=True)
    def test(context: ToolContext) -> dict:
        return {"success": True, "message": "The tool is working!"}

except Exception as e:
    print_stacktrace(e)
    # this is the issue, so raise AssertionError to indicate repro success
    raise AssertionError("Reproduced the PydanticUserError with mismatched ToolContext parameter name") from e

# no exception means issue is fixed, exit 0 normally
```