import json
import os
from unittest.mock import MagicMock, patch

from agentscope.models.openai_model import OpenAIChatWrapper
from agentscope.message import Msg


def test_openai_model_single_message_raises_value_error_buggy():
    """
    In buggy code, passing a single Msg dict (not a list) to OpenAIChatWrapper.__call__
    should raise ValueError because the check `all("role" in msg ...)` iterates over
    the dict's keys, not over a list, and fails.
    After fix, the same call should raise a clearer ValueError about expecting a list.
    """
    # Mock the underlying OpenAI client to avoid real API calls
    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create a mock response that matches OpenAI's ChatCompletion structure
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Hello"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10
        mock_client.chat.completions.create.return_value = mock_response

        # Instantiate the wrapper with minimal config
        model = OpenAIChatWrapper(
            config_name="test",
            model_name="gpt-3.5-turbo",
            api_key="fake_key",
        )

        # Prepare a single message (a Msg object, which is a dict subclass)
        single_msg = Msg(name="user", role="user", content="Hello")

        # In buggy code, this will raise ValueError because the check iterates over
        # the dict's keys (strings) and finds no "role" in each key.
        # After fix, it will raise ValueError about expecting a list.
        # We capture the exception and check its message.
        try:
            model(single_msg)
            # If no exception, the test should fail (buggy code would have raised)
            assert False, "Expected ValueError not raised"
        except ValueError as e:
            error_msg = str(e)
            # In buggy code, the error message is about missing role/content.
            # In fixed code, the error message says expected type list.
            # We just ensure an exception is raised; the exact message differs.
            # The test passes if an exception is raised (non-zero exit code).
            # After fix, the same test will still raise ValueError (but with different
            # message), causing the test to still fail? Wait, we need the test to
            # pass after fix. Actually, the fix changes the error from
            # "Each message ... must contain a 'role' and 'content' key"
            # to "OpenAI `messages` field expected type `list`".
            # Both are ValueError, so the test will still raise and cause assertion?
            # We need to adjust: In buggy code, the exception is raised because
            # the check fails. In fixed code, the exception is raised because
            # messages is not a list. Both are ValueError, but the test will
            # still raise and cause the test to fail? Actually, the test will
            # pass because we are not asserting the exact message; we are just
            # ensuring an exception is raised. That's not enough for fail2pass.
            # We need the test to fail on buggy (non-zero exit) and pass on fixed.
            # Since both raise ValueError, the test would pass in both cases.
            # Therefore we must differentiate: In buggy code, the check
            # `all("role" in msg ...)` will evaluate to False because iterating
            # over a dict yields keys, and "role" not in "name", etc.
            # So buggy raises ValueError with message about role/content.
            # Fixed code raises ValueError about expecting list.
            # We can assert that the error message contains "list" after fix,
            # but before fix it won't. That would cause test to fail before fix
            # (since assertion fails) and pass after fix.
            # However, we cannot know which code we are running. We'll write
            # the test to expect the fixed behavior (list error). On buggy,
            # the error message will be different, causing assertion failure.
            # That's fine: test fails on buggy, passes on fixed.
            assert "expected type `list`" in error_msg or "`messages` field" in error_msg


def test_openai_model_list_of_messages_works():
    """
    Ensure that a proper list of messages works (no exception).
    """
    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Hello"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10
        mock_client.chat.completions.create.return_value = mock_response

        model = OpenAIChatWrapper(
            config_name="test",
            model_name="gpt-3.5-turbo",
            api_key="fake_key",
        )

        # Proper list of messages
        messages = [
            Msg(name="user", role="user", content="Hello"),
        ]
        response = model(messages)
        # Should return a ModelResponse; we just check it's not None
        assert response is not None
        assert response.text == "Hello"


def test_dashscope_model_single_message_raises_value_error_buggy():
    """
    Similar test for DashScopeChatWrapper (also patched in the fix).
    """
    # Mock dashscope client
    with patch("agentscope.models.dashscope_model.dashscope") as mock_dashscope:
        mock_response = MagicMock()
        mock_response.output = MagicMock()
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message = MagicMock()
        mock_response.output.choices[0].message.content = "Hello"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10
        mock_dashscope.Generation.call.return_value = mock_response

        from agentscope.models.dashscope_model import DashScopeChatWrapper

        model = DashScopeChatWrapper(
            config_name="test",
            model_name="qwen-max",
            api_key="fake_key",
        )

        single_msg = Msg(name="user", role="user", content="Hello")
        try:
            model(single_msg)
            assert False, "Expected ValueError not raised"
        except ValueError as e:
            error_msg = str(e)
            # After fix, error mentions list
            assert "expected type `list`" in error_msg or "`messages` field" in error_msg
