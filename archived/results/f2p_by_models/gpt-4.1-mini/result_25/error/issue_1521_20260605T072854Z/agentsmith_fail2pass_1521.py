import os
import pytest

from crewai.agents.parser import _extract_thought


def test_extract_thought_handles_none_input():
    # The function should not raise TypeError when input is None
    result = _extract_thought(None)
    assert result == ""


def test_extract_thought_with_valid_text():
    text = "This is a thought\n\nFinal Answer"
    expected = "This is a thought"
    result = _extract_thought(text)
    assert result == expected


def test_extract_thought_with_text_no_match():
    text = "No matching pattern here"
    result = _extract_thought(text)
    assert result == ""


def test_extract_thought_various_inputs():
    # Test multiple inputs to cover edge cases and expected behavior
    test_cases = [
        (None, ""),
        ("", ""),
        ("Some text\n\nFinal Answer", "Some text"),
        ("No match here", ""),
        ("Thought\n\nAction", "Thought"),
        ("Thought\n\nFinal Answer", "Thought"),
        ("Thought\n\nSomething else", ""),
    ]
    for input_text, expected in test_cases:
        result = _extract_thought(input_text)
        assert result == expected


@pytest.mark.parametrize(
    "input_text,expected",
    [
        (None, ""),
        ("", ""),
        ("Some text\n\nFinal Answer", "Some text"),
        ("No match here", ""),
        ("Thought\n\nAction", "Thought"),
        ("Thought\n\nFinal Answer", "Thought"),
        ("Thought\n\nSomething else", ""),
    ],
)
def test_extract_thought_various_inputs_param(input_text, expected):
    result = _extract_thought(input_text)
    assert result == expected


def test_extract_thought_with_empty_string():
    result = _extract_thought("")
    assert result == ""