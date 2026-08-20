from strands.agent.agent_result import AgentResult
from strands.interrupt import Interrupt
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import Message
from strands.types.streaming import StopReason
from pydantic import BaseModel
import pytest


class StructuredOutputModel(BaseModel):
    name: str
    value: int
    optional_field: str | None = None


@pytest.fixture
def mock_metrics():
    return EventLoopMetrics()


@pytest.fixture
def simple_message() -> Message:
    return {"role": "assistant", "content": [{"text": "Hello world!"}]}


@pytest.fixture
def message_with_structured_and_text() -> Message:
    return {
        "role": "assistant",
        "content": [{"text": "This text should be ignored if structured_output is present"}],
    }


def test__str__with_structured_output(mock_metrics, message_with_structured_and_text: Message):
    """Test that str() returns structured output JSON when structured_output is present."""
    structured_output = StructuredOutputModel(name="test", value=42)

    result = AgentResult(
        stop_reason="end_turn",
        message=message_with_structured_and_text,
        metrics=mock_metrics,
        state={},
        structured_output=structured_output,
    )

    message_string = str(result)
    # The string representation should be the JSON of structured_output, not the message text
    assert message_string == structured_output.model_dump_json()
    assert "test" in message_string
    assert "42" in message_string


def test__str__propagates_both_text_and_structured_output(mock_metrics):
    """Test that both text and structured_output are propagated as expected in AgentResult str()."""
    message = {"role": "assistant", "content": [{"text": "Visible text"}]}
    structured_output = StructuredOutputModel(name="example", value=123)

    result = AgentResult(
        stop_reason="end_turn",
        message=message,
        metrics=mock_metrics,
        state={},
        structured_output=structured_output,
    )

    # The string should be the structured output JSON, not the text
    output_str = str(result)
    assert output_str == structured_output.model_dump_json()
    assert "example" in output_str
    assert "123" in output_str
    assert "Visible text" not in output_str


def test__str__with_interrupts_takes_priority(mock_metrics, simple_message: Message):
    """Test that interrupts take priority over structured_output and text in str()."""
    interrupts = [
        Interrupt(id="int-1", name="approval", reason="Need user approval"),
        Interrupt(id="int-2", name="input", reason="Need more info"),
    ]
    structured_output = StructuredOutputModel(name="test", value=42)

    result = AgentResult(
        stop_reason="end_turn",
        message=simple_message,
        metrics=mock_metrics,
        state={},
        interrupts=interrupts,
        structured_output=structured_output,
    )

    message_string = str(result)
    # Should contain stringified interrupt dicts, not structured output or message text
    assert "int-1" in message_string
    assert "approval" in message_string
    assert "Need user approval" in message_string
    assert "int-2" in message_string
    assert "input" in message_string
    assert "Need more info" in message_string
    assert "test" not in message_string
    assert "42" not in message_string
    assert "Hello world!" not in message_string


def test__str__with_interrupts_over_text(mock_metrics, simple_message: Message):
    """Test that interrupts take priority over message text content in str()."""
    interrupts = [Interrupt(id="int-1", name="confirm", reason="Please confirm")]

    result = AgentResult(
        stop_reason="end_turn",
        message=simple_message,
        metrics=mock_metrics,
        state={},
        interrupts=interrupts,
    )

    message_string = str(result)
    # Should return interrupts, not message text
    assert "int-1" in message_string
    assert "confirm" in message_string
    assert "Hello world!" not in message_string


def test__str__empty_interrupts_falls_back_to_text(mock_metrics, simple_message: Message):
    """Test that empty interrupts list falls through to other content."""
    result = AgentResult(
        stop_reason="end_turn",
        message=simple_message,
        metrics=mock_metrics,
        state={},
        interrupts=[],
    )

    message_string = str(result)
    # Empty list is falsy, should fall through to text content
    assert message_string == "Hello world!\n"


def test__str__with_no_text_but_structured_output(mock_metrics):
    """Test that str() returns structured output JSON when message has no text content."""
    empty_message = {"role": "assistant", "content": []}
    structured_output = StructuredOutputModel(name="example", value=123, optional_field="optional")

    result = AgentResult(
        stop_reason="end_turn",
        message=empty_message,
        metrics=mock_metrics,
        state={},
        structured_output=structured_output,
    )

    message_string = str(result)
    assert message_string == structured_output.model_dump_json()
    assert "example" in message_string
    assert "123" in message_string
    assert "optional" in message_string


def test__str__with_only_text_no_structured_output(mock_metrics, simple_message: Message):
    """Test that str() returns concatenated text when no structured_output or interrupts."""
    result = AgentResult(
        stop_reason="end_turn",
        message=simple_message,
        metrics=mock_metrics,
        state={},
    )

    message_string = str(result)
    assert message_string == "Hello world!\n"


def test__str__with_empty_message_and_no_structured_output(mock_metrics):
    """Test that str() returns empty string when message has no content and no structured_output."""
    empty_message = {"role": "assistant", "content": []}
    result = AgentResult(
        stop_reason="end_turn",
        message=empty_message,
        metrics=mock_metrics,
        state={},
    )

    message_string = str(result)
    assert message_string == ""
