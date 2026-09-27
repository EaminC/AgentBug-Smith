import unittest.mock

import pytest

from strands.handlers.callback_handler import PrintingCallbackHandler


@pytest.fixture
def handler():
    """Create a fresh PrintingCallbackHandler instance for testing."""
    return PrintingCallbackHandler()


@pytest.fixture
def mock_print():
    with unittest.mock.patch("builtins.print") as mock:
        yield mock


def test_call_with_empty_args(handler, mock_print):
    """Test calling the handler with no arguments."""
    handler()
    mock_print.assert_not_called()


def test_call_handler_reasoningText(handler, mock_print):
    """Test calling the handler with reasoningText."""
    handler(reasoningText="This is reasoning text")
    mock_print.assert_called_once_with("This is reasoning text", end="")


def test_call_without_reasoningText(handler, mock_print):
    """Test calling the handler without reasoningText argument."""
    handler(data="Some output")
    mock_print.assert_called_once_with("Some output", end="")


def test_call_with_reasoningText_and_data(handler, mock_print):
    """Test calling the handler with both reasoningText and data."""
    handler(reasoningText="Reasoning", data="Output")
    calls = [
        unittest.mock.call("Reasoning", end=""),
        unittest.mock.call("Output", end=""),
    ]
    mock_print.assert_has_calls(calls)


def test_call_with_data_incomplete(handler, mock_print):
    """Test calling the handler with data but not complete."""
    handler(data="Test output")
    mock_print.assert_called_once_with("Test output", end="")


def test_call_with_data_complete(handler, mock_print):
    """Test calling the handler with data and complete=True."""
    handler(data="Test output", complete=True)
    assert mock_print.call_count == 2
    mock_print.assert_any_call("Test output", end="\n")
    mock_print.assert_any_call("\n")


def test_call_with_tool_uses(handler, mock_print):
    """Test calling the handler with different tool uses."""
    first_event = {"contentBlockStart": {"start": {"toolUse": {"name": "first_tool"}}}}
    second_event = {"contentBlockStart": {"start": {"toolUse": {"name": "second_tool"}}}}

    handler(event=first_event)
    handler(event=second_event)

    assert mock_print.call_args_list == [
        unittest.mock.call("\nTool #1: first_tool"),
        unittest.mock.call("\nTool #2: second_tool"),
    ]

    assert handler.tool_count == 2


def test_call_with_data_and_complete_extra_newline(handler, mock_print):
    """Test that an extra newline is printed when data is complete."""
    handler(data="Test output", complete=True)
    assert mock_print.call_count == 2
    mock_print.assert_any_call("Test output", end="\n")
    mock_print.assert_any_call("\n")


def test_call_with_multiple_parameters(handler, mock_print):
    """Test calling handler with multiple parameters."""
    event = {"contentBlockStart": {"start": {"toolUse": {"name": "test_tool"}}}}

    handler(data="Test output", complete=True, event=event)

    assert mock_print.call_args_list == [
        unittest.mock.call("Test output", end="\n"),
        unittest.mock.call("\nTool #1: test_tool"),
        unittest.mock.call("\n"),
    ]


def test_tool_use_empty_object(handler, mock_print):
    """Test handling of an empty tool use object in event."""
    event = {"contentBlockStart": {"start": {"toolUse": {}}}}

    handler(event=event)

    mock_print.assert_not_called()
    assert handler.tool_count == 0


def test_verbose_tool_use_disabled(mock_print):
    """Test that tool use output is suppressed when verbose_tool_use=False but counting still works."""
    handler = PrintingCallbackHandler(verbose_tool_use=False)
    assert handler._verbose_tool_use is False

    event = {"contentBlockStart": {"start": {"toolUse": {"name": "test_tool"}}}}
    handler(event=event)

    mock_print.assert_not_called()
    assert handler.tool_count == 1
