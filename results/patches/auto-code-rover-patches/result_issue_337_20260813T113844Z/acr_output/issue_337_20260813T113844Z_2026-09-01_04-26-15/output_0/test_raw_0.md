```python
# reproducer.py
from typing import List, Optional
from pydantic import BaseModel, Field
from strands import Agent
from strands.tools import convert_pydantic_to_tool_spec


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


class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: Optional[str] = None


class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class Person(BaseModel):
    """Complete person information."""
    name: str = Field(description="Full name of the person")
    age: int = Field(description="Age in years")
    address: Address = Field(description="Home address")
    contacts: Optional[List[Contact]] = Field(description="Contact methods")
    skills: List[str] = Field(default_factory=list, description="Professional skills")


if __name__ == '__main__':
    import sys
    try:
        tool_spec = convert_pydantic_to_tool_spec(Person)
        # Check that no '$ref' remains inside the schema, especially in contacts
        # This is a simple check; in real cases, references might be nested
        tool_spec_str = str(tool_spec)
        if "'$ref':" in tool_spec_str:
            print("Detected unresolved $ref in tool spec, this is a bug.", file=sys.stderr)
            raise AssertionError("convert_pydantic_to_tool_spec left unresolved $ref in schema")

        agent = Agent()
        result = agent.structured_output(
            Person,
            "Extract info: Jane Doe, a systems admin, 28, lives at 123 Main St, New York, NY"
        )

    except Exception as e:
        print_stacktrace(e)
        # Raise an AssertionError to indicate the issue reproduces
        raise AssertionError("Issue reproduces: Exception thrown during agent structured_output.") from e

    # If we get here, no error means issue is fixed
    sys.exit(0)
```
