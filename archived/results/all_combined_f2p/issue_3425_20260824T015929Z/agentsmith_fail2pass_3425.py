import pytest
from typing import cast

import strands.event_loop.streaming
from strands.types._events import ModelStopReason


def _get_message_from_event(event: ModelStopReason):
    return cast(dict, event["stop"][1])


@pytest.mark.asyncio
async def test_process_stream_with_multiple_signed_reasoning_blocks():
    """Each signed reasoning block keeps only its own signature.

    Guards against https://github.com/strands-agents/harness-sdk/issues/3425: the signature accumulator
    was never cleared when a reasoning block finalized, so later blocks carried a cumulative concatenation
    ("SIG1", "SIG1SIG2", ...) that providers reject as a modified thinking signature on the next request.
    """
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "first"}}, "contentBlockIndex": 0}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"signature": "SIG1"}}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "second"}}, "contentBlockIndex": 1}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"signature": "SIG2"}}, "contentBlockIndex": 1}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]

    async def agenerator(lst):
        for item in lst:
            yield item

    async def alist(agen):
        result = []
        async for item in agen:
            result.append(item)
        return result

    stream = strands.event_loop.streaming.process_stream(agenerator(response))

    last_event = cast(ModelStopReason, (await alist(stream))[-1])

    message = _get_message_from_event(last_event)

    tru_signatures = [block["reasoningContent"]["reasoningText"]["signature"] for block in message["content"]]
    exp_signatures = ["SIG1", "SIG2"]
    assert tru_signatures == exp_signatures


@pytest.mark.asyncio
async def test_process_stream_signature_does_not_leak_into_later_empty_block():
    """A signed reasoning block does not turn a later empty content block into a spurious reasoning block.

    Guards against the secondary effect of https://github.com/strands-agents/harness-sdk/issues/3425: a stale
    signature left in state kept the ``"signature" in state`` guard true, so an otherwise-empty trailing block
    was materialized as a reasoning block carrying the leaked signature.
    """
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "thinking"}}, "contentBlockIndex": 0}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"signature": "SIG1"}}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockStart": {"start": {}, "contentBlockIndex": 1}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]

    async def agenerator(lst):
        for item in lst:
            yield item

    async def alist(agen):
        result = []
        async for item in agen:
            result.append(item)
        return result

    stream = strands.event_loop.streaming.process_stream(agenerator(response))

    last_event = cast(ModelStopReason, (await alist(stream))[-1])

    message = _get_message_from_event(last_event)

    tru_content = message["content"]
    exp_content = [{"reasoningContent": {"reasoningText": {"text": "thinking", "signature": "SIG1"}}}]
    assert tru_content == exp_content
