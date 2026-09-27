import sys
from pathlib import Path
from unittest.mock import patch

# 1. Ensure /app has precedence in Python's import search path
app_dir = str(Path("/app").resolve())
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from interpreter.terminal_interface.render_past_conversation import render_past_conversation


def test_render_past_conversation_streaming_format():
    """
    Issue #962 / PR #977:
    render_past_conversation must support the 0.2.0 streaming format
    using 'content', 'type', and 'format' keys instead of legacy keys
    'message', 'code', 'language', and 'output'.
    """
    past_messages = [
        {
            "role": "user",
            "type": "message",
            "content": "Can you print hello world?",
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "Sure! Here is the Python code:",
        },
        {
            "role": "assistant",
            "type": "code",
            "format": "python",
            "content": "print('Hello world!')",
            "active_line": 1,
        },
        {
            "role": "assistant",
            "type": "console",
            "content": "Hello world!",
        },
    ]

    # Suppress console printing during test execution
    with patch("builtins.print"):
        # Pre-patch (Base commit 65102503...):
        # Line 25 checks chunk["message"] on role=="user" chunk -> raises KeyError: 'message' (FAILS, rc1=1)
        #
        # Post-patch (PR #977):
        # Line 25 checks chunk["content"] and updates types -> passes cleanly (PASSES, rc2=0)
        render_past_conversation(past_messages)