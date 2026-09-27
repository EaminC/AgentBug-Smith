```python
# reproducer.py

from strands import Agent, tool
from strands.models import BedrockModel
import sys

def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


@tool
def get_user_info() -> dict:
    """Get user information."""
    return {"name": "Alice", "card": "LIB-456789"}

@tool
def get_book_status(book_id: str) -> dict:
    """Get book status."""
    return {"book_id": book_id, "status": "ACTIVE"}

def main():
    agent = Agent(
        model=BedrockModel(model_id="qwen.qwen3-next-80b-a3b"),
        tools=[get_user_info, get_book_status],
        system_prompt="You are a helpful assistant."
    )

    # Intercept printed output of tools for observation
    import io
    import contextlib

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = agent("Please check the status of book BOOK-123")
    printed = output.getvalue()

    # According to the bug description,
    # get_user_info tool is executed during reasoning but never printed.
    # Only get_book_status is printed as Tool #1

    try:
        # Check that both tools executed are printed
        # The reproduced output will only show "Tool #1: get_book_status" currently.
        # We assert that the first tool get_user_info was also printed to stdout.
        # We'll look for a printed line with "Tool #X: get_user_info"
        user_info_printed = any(
            line.strip().endswith("get_user_info") for line in printed.splitlines()
            if line.strip().startswith("Tool #")
        )
        if not user_info_printed:
            raise AssertionError(
                "Tool call to get_user_info executed during reasoning phase but NOT displayed to user.\n"
                "This reproduces the bug described: tools executed silently during reasoning are missing from callback prints."
            )
    except Exception as e:
        print_stacktrace(e)
        raise

if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
    # Exit 0 means issue fixed, all tools printed
    sys.exit(0)
```
