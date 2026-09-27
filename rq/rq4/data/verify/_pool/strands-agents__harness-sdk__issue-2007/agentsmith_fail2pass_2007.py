import unittest.mock
import pytest

import strands
from strands.models.ollama import OllamaModel


@pytest.fixture
def ollama_client():
    with unittest.mock.patch.object(strands.models.ollama.ollama, "AsyncClient") as mock_client_cls:
        yield mock_client_cls.return_value


@pytest.fixture
def model_id():
    return "m1"


@pytest.fixture
def host():
    return "h1"


@pytest.fixture
def model(model_id, host):
    return OllamaModel(host, model_id=model_id)


@pytest.mark.asyncio
async def test_format_chunk_metadata(model):
    event = {
        "chunk_type": "metadata",
        "data": unittest.mock.Mock(eval_count=100, prompt_eval_count=50, total_duration=1000000),
    }

    tru_chunk = model.format_chunk(event)
    exp_chunk = {
        "metadata": {
            "usage": {
                "inputTokens": 50,
                "outputTokens": 100,
                "totalTokens": 150,
            },
            "metrics": {
                "latencyMs": 1.0,
            },
        },
    }

    assert tru_chunk == exp_chunk


@pytest.mark.asyncio
async def test_stream(ollama_client, model, agenerator, alist, captured_warnings):
    mock_event = unittest.mock.Mock()
    mock_event.message.tool_calls = None
    mock_event.message.content = "Hello"
    mock_event.done_reason = "stop"
    mock_event.eval_count = 10
    mock_event.prompt_eval_count = 5
    mock_event.total_duration = 1000000  # 1ms in nanoseconds

    ollama_client.chat = unittest.mock.AsyncMock(return_value=agenerator([mock_event]))

    messages = [{"role": "user", "content": [{"text": "Hello"}]}]
    response = model.stream(messages)

    tru_events = await alist(response)
    exp_events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {}}},
        {"contentBlockDelta": {"delta": {"text": "Hello"}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {"inputTokens": 5, "outputTokens": 10, "totalTokens": 15},
                "metrics": {"latencyMs": 1.0},
            }
        },
    ]

    assert tru_events == exp_events
    expected_request = {
        "model": "m1",
        "messages": [{"role": "user", "content": "Hello"}],
        "options": {},
        "stream": True,
        "tools": [],
    }
    ollama_client.chat.assert_called_once_with(**expected_request)

    # Ensure no warnings emitted
    assert len(captured_warnings) == 0


@pytest.mark.asyncio
async def test_stream_with_tool_calls(ollama_client, model, agenerator, alist):
    mock_event = unittest.mock.Mock()
    mock_tool_call = unittest.mock.Mock()
    mock_tool_call.function.name = "calculator"
    mock_tool_call.function.arguments = {"expression": "2+2"}
    mock_event.message.tool_calls = [mock_tool_call]
    mock_event.message.content = "I'll calculate that for you"
    mock_event.done_reason = "stop"
    mock_event.eval_count = 15
    mock_event.prompt_eval_count = 8
    mock_event.total_duration = 2000000  # 2ms in nanoseconds

    ollama_client.chat = unittest.mock.AsyncMock(return_value=agenerator([mock_event]))

    messages = [{"role": "user", "content": [{"text": "Calculate 2+2"}]}]
    response = model.stream(messages)

    tru_events = await alist(response)
    exp_events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {}}},
        {"contentBlockStart": {"start": {"toolUse": {"name": "calculator", "toolUseId": "calculator"}}}},
        {"contentBlockDelta": {"delta": {"toolUse": {"input": '{"expression": "2+2"}'}}}},
        {"contentBlockStop": {}},
        {"contentBlockDelta": {"delta": {"text": "I'll calculate that for you"}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
        {
            "metadata": {
                "usage": {"inputTokens": 8, "outputTokens": 15, "totalTokens": 23},
                "metrics": {"latencyMs": 2.0},
            }
        },
    ]

    assert tru_events == exp_events
    expected_request = {
        "model": "m1",
        "messages": [{"role": "user", "content": "Calculate 2+2"}],
        "options": {},
        "stream": True,
        "tools": [],
    }
    ollama_client.chat.assert_called_once_with(**expected_request)
