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
import logging

from agentscope import agentscope
from agentscope.models import OllamaChatWrapper


def test_ollama_chatwrapper_format_issue():
    # Setup a minimal dummy config to initialize agentscope with ollama_chat llama3.1, as per issue repro steps
    model_config = {
        "model_type": "ollama_chat",
        "config_name": "ollama",
        "model_name": "llama3.1",
    }

    # Initialize agentscope with the model config
    agentscope.init(
        model_configs=[model_config],
        # possibly other init parameters minimal to run
        # since issue references conversation.py example, just minimal init
    )

    # Create an instance of OllamaChatWrapper directly to test the format behavior
    # We import and call the format method to check roles set

    # Construct test input messages
    # According to docstring, role in input to format should be "user"
    # But actual implementation sets role='system', causing the problem

    # We test if the formatted messages are set with role="user" (the docstring)
    # or wrongly role="system" (the bug), by manually calling format
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]
    # Create wrapper instance
    wrapper = OllamaChatWrapper(model_name="llama3.1")

    # We call the internal format method, which returns a list of dict messages
    formatted = wrapper.format(messages)

    # Check if all user messages became system role (which is the bug)
    roles = [m["role"] for m in formatted]

    # The bug: all roles are "system"
    # The fix: user messages remain user role, system messages remain system

    # If bug present, user message role is replaced wrongly with system
    # So raise AssertionError if any input message with role "user" is converted to "system"

    try:
        for i, (in_msg, out_msg) in enumerate(zip(messages, formatted)):
            if in_msg["role"] == "user":
                # We expect role remains "user"
                assert (
                    out_msg["role"] == "user"
                ), f"Bug detected: message {i} role changed from user to {out_msg['role']}"
        print("No bug detected: user messages correctly formatted with role 'user'.")
    except AssertionError as e:
        # Print stacktrace and re-raise to exit with error code
        print_stacktrace(e)
        raise


if __name__ == "__main__":
    try:
        test_ollama_chatwrapper_format_issue()
    except AssertionError:
        sys.exit(1)
    sys.exit(0)
```
