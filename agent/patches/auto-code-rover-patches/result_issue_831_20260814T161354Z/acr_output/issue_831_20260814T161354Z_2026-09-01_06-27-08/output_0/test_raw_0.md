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
    from pydantic import BaseModel, Field
    from strands.models import BedrockModel
    from strands import Agent

    class ContactCard(BaseModel):
        name: str = Field(description="The name of the person")
        age: int = Field(description="The age of the person")
        address: str = Field(description="The address of the person")

    # Create BedrockModel with custom timeout configuration
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name='us-west-2',
        additional_request_fields={
            "thinking": {
                "type": "enabled",
                "budget_tokens": 2048
            }
        }
    )

    system_prompt = "you are a helpful document understanding agent. You parse documetns into structured data"

    events = []

    def grab_event_callback(**kwargs):
        events.append(kwargs)

    agent = Agent(
        model=bedrock_model,
        system_prompt=system_prompt,
        callback_handler=grab_event_callback
    )

    try:
        cc = agent.structured_output(
            ContactCard,
            "Convert the following data to a contact card <input> John, last name Smith, who resides at 123 anytown usa, Texas, 78756, and is of age 38</input>"
        )
        # If callback is working correctly, events should not be empty
        if not events:
            raise AssertionError("CallbackHandler was not invoked; events list is empty")
    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

    sys.exit(0)
```
