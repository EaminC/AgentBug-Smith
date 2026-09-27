```python
# reproducer.py
from strands import tool
from enum import Enum
import json
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

class Priority(str, Enum):
    A = 'A'
    B = 'B'

@tool
def my_tool(
    required_field: str,
    priority: Priority | None,  # Required but nullable
) -> str:
    """Test tool.

    Args:
        required_field: A required string
        priority: Optional priority level
    """
    return str(priority)

def main():
    # Check the generated schema
    schema = my_tool.tool_spec['inputSchema']['json']
    # Extract priority schema
    priority_schema = schema['properties']['priority']

    # The expected schema fragment for priority (null explicitly allowed in anyOf)
    # We'll check that either:
    # 1) 'anyOf' exists with an item having type "null"
    # or
    # 2) The field priority is NOT required or nullable is allowed by some other mechanism
    # But the current issue is that 'anyOf' is stripped
    try:
        # Check if nullable is preserved in the schema for 'priority'
        # Expected to have 'anyOf' with null type included
        null_in_anyof = False
        if 'anyOf' in priority_schema:
            anyof = priority_schema['anyOf']
            null_in_anyof = any(item.get('type') == 'null' for item in anyof)
        else:
            # No 'anyOf' means the null type was stripped -> bug present
            null_in_anyof = False

        # The 'priority' argument is annotated as Optional, so null must be allowed:
        # Also assert that 'priority' is still in 'required' since marked required but nullable
        required_fields = schema.get('required', [])
        is_priority_required = 'priority' in required_fields

        # The bug: null_in_anyof == False and is_priority_required == True => bad
        # Because null is stripped but field still required
        if not null_in_anyof and is_priority_required:
            raise AssertionError(
                "BUG: @tool decorator strips null from Optional/Union type but keeps field as required. "
                "Schema for priority: " + json.dumps(priority_schema, indent=2) +
                "\nRequired fields: " + str(required_fields)
            )
        # If we get here, either null is preserved or field is optional, so no problem
        print("No issue detected: nullable type is preserved or field is not required.")

    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

if __name__ == '__main__':
    main()
```