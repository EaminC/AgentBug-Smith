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


import json
import sys
from typing import Union
from strands import tool

@tool
def sleep(seconds: Union[int, float]) -> str:
    """
    Pause execution for the specified number of seconds.

    This tool pauses the execution flow for the given number of seconds.
    It can be interrupted with SIGINT (Ctrl+C).

    Args:
        seconds (Union[int, float]): Number of seconds to sleep.
            Must be a positive number greater than 0 and less than or equal to
            the maximum allowed value (default: 300 seconds, configurable via
            MAX_SLEEP_SECONDS environment variable).

    Returns:
        str: A message indicating the sleep completed or was interrupted.

    Raises:
        ValueError: If seconds is not positive, exceeds the maximum allowed value,
                   or is not a number.

    Examples:
        >>> sleep(5)  # Sleeps for 5 seconds
        'Started sleep at 2025-05-30 11:30:00, slept for 5.0 seconds'

        >>> sleep(0.5)  # Sleeps for half a second
        'Started sleep at 2025-05-30 11:30:00, slept for 0.5 seconds'
    """
    pass

# Extract tool spec
tool_spec = sleep.tool_spec

# Check if the description includes "Args:" section or other sections beyond the first paragraph
description = tool_spec.get("description", "")

# According to the expected behavior, description should be short, e.g. only first paragraph.
# It should NOT contain lines starting with Args:, Returns:, Raises:, Examples:
sections = ["Args:", "Returns:", "Raises:", "Examples:"]

try:
    for section in sections:
        if section in description:
            raise AssertionError(
                f"Found section '{section}' in tool description, but only first paragraph expected"
            )
except Exception as e:
    print_stacktrace(e)
    sys.exit(1)

# If none of the bad sections are found, the issue is presumed fixed
sys.exit(0)
```
