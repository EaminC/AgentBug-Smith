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


def main():
    import sys
    from agentscope.model import OpenAIChatModel

    # The Qwen model id (replace with the actual Qwen model identifier in the deployment)
    model_id = "openai_chat_qwen"  # replace with actual Qwen OpenAI-compatible model name

    # Configure model with thinking_enable True, but attempt to turn it off later
    # The issue is that thinking_enable is not passed correctly into extra_body.enable_thinking
    # So user cannot disable thinking mode when structured output is requested

    # We try thinking_enable=False here to test if it is forwarded correctly
    model = OpenAIChatModel(
        model=model_id,
        thinking_enable=False,  # Intend to disable thinking mode
    )
    # Provide a simple message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say a number in JSON: {\"number\": 42}"}
    ]

    # Prepare a simple structured output schema forcing JSON output (simulate structured_model)
    # Using a minimal schema that requires a number field
    # Structured model here would be an OpenAIChatModel-compatible structured model
    # This is a minimal mock / example, replace with actual schema if possible
    from agentscope.schema import ChatCompletionStructuredModel, StructuredOutputSchemaProperty, StructuredOutputSchemaType

    schema = ChatCompletionStructuredModel(
        type=StructuredOutputSchemaType.OBJECT,
        properties={
            "number": StructuredOutputSchemaProperty(type="integer", description="A number in output")
        },
        required=["number"],
    )

    try:
        # This call should send thinking_enable=False into extra_body to disable thinking mode
        # If thinking_enable is NOT forwarded, thinking mode stays ON, causing error in structured output
        response = model(messages, structured_model=schema)

    except Exception as e:
        # If we hit the thinking mode / structured output incompatibility error, print stack trace and assert
        # Example error message from the issue:
        # openai.BadRequestError: ... InvalidParameter: The tool_choice parameter does not support being set ...
        print_stacktrace(e)
        # We consider the issue present if the exception message contains key keywords
        err_msg_lower = str(e).lower()
        if "invalidparameter" in err_msg_lower or "thinking mode" in err_msg_lower or "enable_thinking" in err_msg_lower:
            raise AssertionError(
                "Bug present: thinking_enable parameter not passed correctly, thinking mode active during structured output"
            ) from e

        # If other error, re-raise
        raise

    # If no error, then thinking_enable was passed properly and thinking mode disabled correctly
    print("No issue detected: thinking_enable parameter passed correctly and thinking mode disabled as expected.")
    sys.exit(0)


if __name__ == "__main__":
    import sys
    try:
        main()
    except AssertionError as e:
        # Exit with code 1 for bug presence
        sys.exit(1)
    except Exception as e:
        # Print any unexpected error and exit with 1
        print_stacktrace(e)
        sys.exit(1)
```
