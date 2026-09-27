import pytest
import strands.event_loop.streaming
from strands.types._events import ModelStopReason
from typing import cast


def test_handle_message_stop():
    event: strands.event_loop.streaming.MessageStopEvent = {"stopReason": "end_turn"}

    tru_reason = strands.event_loop.streaming.handle_message_stop(event, [])
    exp_reason = "end_turn"

    assert tru_reason == exp_reason


def test_handle_message_stop_overrides_end_turn_when_tool_use_present():
    event: strands.event_loop.streaming.MessageStopEvent = {"stopReason": "end_turn"}
    content = [{"toolUse": {"toolUseId": "t1", "name": "myTool", "input": {}}}]

    tru_reason = strands.event_loop.streaming.handle_message_stop(event, content)

    assert tru_reason == "tool_use"


def test_handle_message_stop_keeps_tool_use_unchanged():
    event: strands.event_loop.streaming.MessageStopEvent = {"stopReason": "tool_use"}
    content = [{"toolUse": {"toolUseId": "t1", "name": "myTool", "input": {}}}]

    tru_reason = strands.event_loop.streaming.handle_message_stop(event, content)

    assert tru_reason == "tool_use"


@pytest.mark.asyncio
async def test_process_stream_overrides_end_turn_when_tool_use_present(agenerator, alist):
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"toolUseId": "t1", "name": "myTool"}}}},
        {"contentBlockDelta": {"delta": {"toolUse": {"input": '{"key": "val"}'}}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
                "metrics": {"latencyMs": 100},
            }
        },
    ]

    stream = strands.event_loop.streaming.process_stream(agenerator(response))
    last_event = cast(ModelStopReason, (await alist(stream))[-1])

    assert last_event["stop"][0] == "tool_use"


@pytest.mark.asyncio
async def test_process_stream_keeps_end_turn_when_no_tool_use(agenerator, alist):
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"delta": {"text": "Hello!"}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
                "metrics": {"latencyMs": 100},
            }
        },
    ]

    stream = strands.event_loop.streaming.process_stream(agenerator(response))
    last_event = cast(ModelStopReason, (await alist(stream))[-1])

    assert last_event["stop"][0] == "end_turn"


@pytest.mark.asyncio
async def test_process_stream_keeps_tool_use_stop_reason_unchanged(agenerator, alist):
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"toolUseId": "t1", "name": "myTool"}}}},
        {"contentBlockDelta": {"delta": {"toolUse": {"input": "{}"}}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "tool_use"}},
        {
            "metadata": {
                "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
                "metrics": {"latencyMs": 100},
            }
        },
    ]

    stream = strands.event_loop.streaming.process_stream(agenerator(response))
    last_event = cast(ModelStopReason, (await alist(stream))[-1])

    assert last_event["stop"][0] == "tool_use"
