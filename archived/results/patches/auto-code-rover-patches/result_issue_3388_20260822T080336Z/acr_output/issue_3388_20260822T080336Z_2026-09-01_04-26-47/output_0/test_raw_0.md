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
    import json

    # Emulate minimal parts of the OpenAI Responses TypeScript adapter serialization in Python,
    # reproducing the known bad shape:
    #
    # For a two-turn conversation:
    # Assistant message output as:
    #   { "role": "assistant", "content": [{ "type": "output_text", "text": "..." }] }
    #
    # This is invalid for the Bedrock Mantle interface,
    # which expects either a string content (EasyInputMessage) or full ResponseOutputMessage with required fields.

    def format_responses_messages(messages):
        """
        Simulates the broken serialization that sends bare
        output_text content as an array with just {type, text}
        for assistant messages (incorrect shape):
        """
        result = []
        for m in messages:
            if m["role"] == "assistant":
                # Incorrect assistant shape with content array of output_text fragment
                result.append({
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": m["content"]}]
                })
            else:
                # Keep user as is: content string
                result.append(m)
        return result

    # Prepare a conversation: user says "hello", assistant replies "world"
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},  # raw string here; will become content=[{type:output_text,...}]
    ]

    # Serialize messages using broken adapter
    serialized = format_responses_messages(messages)

    # Bedrock Mantle expects valid shape:
    # For assistant message:
    # - content is string OR full ResponseOutputMessage with keys:
    #   type: "message", id, status, output_text (which includes annotations array).

    # We assert that the assistant message shape is invalid:
    # It must not be simply {role: assistant, content: [{type: "output_text", text: "..."}]}

    try:
        for msg in serialized:
            if msg["role"] == "assistant":
                c = msg["content"]
                # Content should be string or check if it's properly shaped dict
                # Here we expect a string or a dict with "type"=="message"
                if isinstance(c, list):
                    # This is the problem: content is a list of output_text dict(s)
                    # Validate that this is invalid
                    for item in c:
                        if not (isinstance(item, dict) and item.get("type") == "message"):
                            # Detected invalid content shape
                            raise AssertionError(
                                "Invalid assistant message content shape detected: "
                                f"{json.dumps(msg, indent=2)}"
                            )
                elif isinstance(c, str):
                    # string content is valid, no problem
                    pass
                else:
                    # unexpected content type
                    raise AssertionError(
                        f"Unexpected assistant content type: {type(c)}"
                    )
    except Exception as e:
        print_stacktrace(e)
        # Exit with failure status code, showing the failure
        sys.exit(1)

    # If no invalid shape found, pass quietly
    print("No invalid assistant history shape detected. Issue is fixed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```
