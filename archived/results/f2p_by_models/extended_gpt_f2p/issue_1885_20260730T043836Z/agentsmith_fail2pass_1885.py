import asyncio
import pytest
from src.agentscope.message import TextBlock, ThinkingBlock
from src.agentscope.model import ChatResponse
from src.agentscope.agent._agent import Agent


@pytest.mark.asyncio
async def test_thinking_block_end_before_text_block_delta():
    """
    Regression test for issue #1885:
    Ensure that ThinkingBlockEndEvent is emitted before any TextBlockDeltaEvent at the reasoning->answer boundary.
    """

    class _Stub:
        class state:
            reply_id = "r"

    convert = Agent._convert_chat_response_to_event.__get__(_Stub())

    # A well-behaved reasoning stream: reasoning fully precedes the answer,
    # delivered in SEPARATE chunks (how DeepSeek / Qwen reasoning models stream).
    chunks = [
        ChatResponse(content=[ThinkingBlock(thinking="reason")], is_last=False),
        ChatResponse(content=[TextBlock(text="Hello")], is_last=False),  # boundary: reasoning done, answer begins
    ]

    block_ids = {"text": None, "thinking": None, "tools": []}
    seq = []
    for ch in chunks:
        async for ev in convert(block_ids, ch):
            seq.append(type(ev).__name__)

    # The expected order is that the ThinkingBlockEndEvent comes before any TextBlockDeltaEvent
    # so that the first answer token is not trapped inside the thinking block.
    # Expected sequence:
    # ThinkingBlockStartEvent -> ThinkingBlockDeltaEvent -> ThinkingBlockEndEvent -> TextBlockStartEvent -> TextBlockDeltaEvent
    expected_order = [
        "ThinkingBlockStartEvent",
        "ThinkingBlockDeltaEvent",
        "ThinkingBlockEndEvent",
        "TextBlockStartEvent",
        "TextBlockDeltaEvent",
    ]

    # Assert that the actual sequence matches the expected sequence exactly
    assert seq == expected_order, f"Event sequence incorrect: {seq}"
