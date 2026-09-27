import json
import math
import pytest
from strands.models.model import _estimate_tokens_with_heuristic


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_json():
    obj = {"x": "lorem ipsum " * 1000}
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "123",
                        "content": [{"json": obj}],
                        "status": "success",
                    }
                }
            ],
        }
    ]
    # Use the heuristic function directly to test the token count
    tokens = _estimate_tokens_with_heuristic(messages)
    # The tokens should be approximately ceil(len(json.dumps(obj)) / 2)
    expected = math.ceil(len(json.dumps(obj)) / 2)
    assert tokens == expected
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_text_and_json():
    text = "Here is the data"
    obj = {"key": "value", "count": 42}
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "123",
                        "content": [
                            {"text": text},
                            {"json": obj},
                        ],
                        "status": "success",
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    expected = math.ceil(len(text) / 4) + math.ceil(len(json.dumps(obj)) / 2)
    assert tokens == expected
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_json_and_other_blocks():
    # Test a message with toolResult containing json, plus other content types
    obj = {"data": [1, 2, 3]}
    messages = [
        {"role": "user", "content": [{"text": "hello"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "1", "name": "my_tool", "input": {"q": "test"}}},
                {"reasoningContent": {"reasoningText": {"text": "Thinking..."}}},
                {"guardContent": {"text": {"text": "Filtered content"}}},
                {"citationsContent": {"content": [{"text": "Citation here"}]}},
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "1",
                        "content": [
                            {"json": obj},
                            {"text": "tool output here"},
                        ],
                        "status": "success",
                    }
                }
            ],
        },
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_json_zero_before_fix():
    # This test is a reproduction of the original bug:
    # Before fix, the count_tokens returns 0 for toolResult with json content.
    # After fix, it returns > 0.
    # We assert > 0 here to fail on buggy code.
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "status": "success",
                        "content": [{"json": {"x": "lorem ipsum " * 1000}}],
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_empty_json():
    # Test with empty json content, should count tokens > 0 because json.dumps("{}") length > 0
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "status": "success",
                        "content": [{"json": {}}],
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_non_json_content_only():
    # Test that toolResult with only image content returns 0 tokens (binary skipped)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "status": "success",
                        "content": [{"image": {"format": "png", "source": {"bytes": b"fake"}}}],
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    assert tokens == 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_text_and_image():
    # Test that toolResult with text and image counts only text tokens > 0
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "status": "success",
                        "content": [
                            {"text": "some text"},
                            {"image": {"format": "png", "source": {"bytes": b"fake"}}},
                        ],
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    assert tokens > 0


@pytest.mark.asyncio
async def test_count_tokens_tool_result_with_json_and_bytes():
    # Mixed json and bytes content, only json counted
    obj = {"key": "value"}
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "status": "success",
                        "content": [
                            {"json": obj},
                            {"image": {"format": "png", "source": {"bytes": b"fake"}}},
                        ],
                    }
                }
            ],
        }
    ]
    tokens = _estimate_tokens_with_heuristic(messages)
    expected = math.ceil(len(json.dumps(obj)) / 2)
    assert tokens == expected
    assert tokens > 0
