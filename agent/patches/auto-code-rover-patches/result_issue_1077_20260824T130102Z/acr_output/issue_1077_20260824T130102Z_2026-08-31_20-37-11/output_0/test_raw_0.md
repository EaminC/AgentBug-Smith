```python
# reproducer.py
import json
import sys
import traceback

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


try:
    import boto3
    from strands import Agent, tool
    from strands.models import BedrockModel
except ImportError:
    print("This reproducer requires strands and boto3 packages installed.", file=sys.stderr)
    sys.exit(1)


def get_guardrail():
    client = boto3.client("bedrock", region_name="us-west-2")

    guardrail_name = "test-guardrail-block-cactus"
    response = client.list_guardrails()
    for guardrail in response.get("guardrails", []):
        if guardrail["name"] == guardrail_name:
            return guardrail["id"]
    return None


@tool
def get_users() -> str:
    "List my users"
    return (
        "|Name|Email|\n"
        "|Jerry Barry|jerry@gmail.com|\n"
        "|CACTUS|cactus@email.com|\n"
    )


def main():
    guardrail_id = get_guardrail()
    if not guardrail_id:
        print(
            'Guardrail "test-guardrail-block-cactus" not found in Bedrock. '
            "Please create it before running this reproducer.",
            file=sys.stderr,
        )
        sys.exit(2)

    bedrock_model = BedrockModel(
        model_id="...",  # Replace with your actual Bedrock model id
        guardrail_id=guardrail_id,
        guardrail_version="DRAFT",
        guardrail_redact_input=True,  # default
        guardrail_redact_output=False,  # default
    )

    agent = Agent(
        system_prompt="You are a helpful assistant.",
        model=bedrock_model,
        tools=[get_users],
    )

    try:
        response = agent("Who are my users?")
        # The issue manifests as guardrail_intervened stop reason, with redacted tool output input,
        # causing next calls to error.
        assert (
            response.stop_reason == "guardrail_intervened"
        ), f"Expected stop_reason 'guardrail_intervened', got '{response.stop_reason}'"
    except Exception as e:
        print("Exception during first agent call:", file=sys.stderr)
        print_stacktrace(e)
        # We consider a failure to get guardrail_intervened to be an issue,
        # so exit 1 to mark the test failed.
        sys.exit(1)

    # Print conversation after first call - useful to see redaction behavior
    print(f"Conversation after first call: {json.dumps(agent.messages, indent=4)}")

    try:
        # Make a second call to reproduce the broken conversation history error
        response = agent("Hello")
        # This call should succeed if fix is present
    except Exception as e:
        print("Exception during second agent call:", file=sys.stderr)
        print_stacktrace(e)
        # This exception indicates redaction of tool outputs breaking conversation
        # So assert failure (issue present)
        raise AssertionError(
            "Agent conversation broke due to tool_result redaction after guardrail intervention."
        ) from e

    # If we reach here, issue is fixed
    print("Reproducer ran successfully, issue not present.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```
