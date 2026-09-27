import json
import pytest

from strands.models.openai import OpenAIModel


def test_format_request_tool_message_multi_text_returns_joined_string():
    """Test that multi-content text results are joined into a single string.

    Regression test for https://github.com/strands-agents/sdk-python/issues/1696.
    OpenAI-compatible endpoints (e.g., Kimi K2.5, vLLM, Ollama) only correctly
    parse string content for tool messages; array format causes hallucinated results.
    """
    tool_result = {
        "content": [
            {"text": "Temperature: 72°F"},
            {"json": {"humidity": 45, "unit": "%"}},
            {"text": "Wind: 5 mph"},
        ],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    exp_result = {
        "content": 'Temperature: 72°F\n{"humidity": 45, "unit": "%"}\nWind: 5 mph',
        "role": "tool",
        "tool_call_id": "c1",
    }
    assert tru_result == exp_result


def test_format_request_tool_message_mixed_text_image_preserves_order():
    """Test that text and image content blocks preserve their original order."""
    tool_result = {
        "content": [
            {"text": "Before image"},
            {"image": {"format": "png", "source": {"bytes": b"PNG"}}},
            {"text": "After image"},
        ],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    content = tru_result["content"]
    # Array format since images are present
    assert isinstance(content, list)
    assert len(content) == 3
    # Order preserved: text, image, text
    assert content[0] == {"type": "text", "text": "Before image"}
    assert content[1]["type"] == "image_url"
    assert content[2] == {"type": "text", "text": "After image"}


def test_format_request_tool_message_merges_adjacent_text():
    """Test that adjacent text blocks are merged while non-text order is preserved."""
    tool_result = {
        "content": [
            {"text": "Line 1"},
            {"text": "Line 2"},
            {"image": {"format": "png", "source": {"bytes": b"PNG"}}},
            {"text": "Line 3"},
        ],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    content = tru_result["content"]
    assert isinstance(content, list)
    assert len(content) == 3
    # Adjacent text merged, image order preserved
    assert content[0] == {"type": "text", "text": "Line 1\nLine 2"}
    assert content[1]["type"] == "image_url"
    assert content[2] == {"type": "text", "text": "Line 3"}


def test_format_request_tool_message_image_only():
    """Test tool message with only non-text content."""
    tool_result = {
        "content": [
            {"image": {"format": "png", "source": {"bytes": b"PNG"}}},
        ],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    content = tru_result["content"]
    assert isinstance(content, list)
    assert len(content) == 1
    assert content[0]["type"] == "image_url"


def test_format_request_tool_message_document_mixed():
    """Test tool message with document content mixed with text."""
    tool_result = {
        "content": [
            {"text": "Summary"},
            {"document": {"format": "pdf", "name": "report.pdf", "source": {"bytes": b"PDF"}}},
            {"text": "Footer"},
        ],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    content = tru_result["content"]
    assert isinstance(content, list)
    assert len(content) == 3
    assert content[0] == {"type": "text", "text": "Summary"}
    assert content[1]["type"] == "file"
    assert content[2] == {"type": "text", "text": "Footer"}


def test_format_request_tool_message_empty_content():
    """Test tool message with empty content list returns empty string."""
    tool_result = {
        "content": [],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    assert tru_result["content"] == ""
    assert tru_result["role"] == "tool"
    assert tru_result["tool_call_id"] == "c1"


def test_format_request_tool_message_single_text_returns_string():
    """Test that single text content is returned as string for model compatibility."""
    tool_result = {
        "content": [{"text": '{"result": "success"}'}],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    exp_result = {
        "content": '{"result": "success"}',
        "role": "tool",
        "tool_call_id": "c1",
    }
    assert tru_result == exp_result


def test_format_request_tool_message_original_array_format_fails():
    """This test verifies that the original buggy behavior (array content) is not equal to the fixed string content.

    This test is expected to fail on the buggy codebase and pass after the fix.
    """
    tool_result = {
        "content": [{"text": "4"}, {"json": ["4"]}],
        "status": "success",
        "toolUseId": "c1",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    # The buggy code returns content as list of dicts; the fixed code returns a joined string.
    # We assert that the content is a string, not a list, to catch the bug.
    assert isinstance(tru_result["content"], str)
    # Also assert the string contains both parts joined by newline
    assert tru_result["content"] == '4\n["4"]'
    # The role and tool_call_id must be correct
    assert tru_result["role"] == "tool"
    assert tru_result["tool_call_id"] == "c1"


def test_format_request_tool_message_content_order_and_merge():
    """Test that the content order is preserved and adjacent text blocks merged correctly."""
    tool_result = {
        "content": [
            {"text": "First line"},
            {"text": "Second line"},
            {"image": {"format": "png", "source": {"bytes": b"data"}}},
            {"text": "Third line"},
            {"document": {"format": "pdf", "name": "doc.pdf", "source": {"bytes": b"pdfdata"}}},
            {"text": "Fourth line"},
        ],
        "status": "success",
        "toolUseId": "tool123",
    }

    tru_result = OpenAIModel.format_request_tool_message(tool_result)
    content = tru_result["content"]
    assert isinstance(content, list)
    # Expect 5 content blocks: merged first two text, image, text, document, text
    # Actually merged first two text into one, then image, then text, then document, then text
    # So total 5 blocks
    assert len(content) == 5
    assert content[0] == {"type": "text", "text": "First line\nSecond line"}
    assert content[1]["type"] == "image_url"
    assert content[2] == {"type": "text", "text": "Third line"}
    assert content[3]["type"] == "file"
    assert content[4] == {"type": "text", "text": "Fourth line"}
    assert tru_result["role"] == "tool"
    assert tru_result["tool_call_id"] == "tool123"
