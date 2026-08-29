import pytest
from unittest.mock import patch

from crewai.llm import CONTEXT_WINDOW_USAGE_RATIO, LLM


def test_context_window_o3_mini():
    """Test that the context window size for 'o3-mini' is set correctly to 200000 * usage ratio."""
    llm = LLM(model="o3-mini")
    expected_context_window = int(200000 * CONTEXT_WINDOW_USAGE_RATIO)
    actual_context_window = llm.get_context_window_size()
    assert actual_context_window == expected_context_window, (
        f"Expected context window size {expected_context_window} for 'o3-mini', "
        f"got {actual_context_window}"
    )


def test_context_window_validation_raises_for_invalid_size():
    """Test that get_context_window_size raises ValueError for invalid context window sizes."""

    with patch.dict(
        "crewai.llm.LLM_CONTEXT_WINDOW_SIZES",
        {"invalid-model": 500},  # Below minimum allowed 1024
        clear=True,
    ):
        llm = LLM(model="invalid-model")
        with pytest.raises(ValueError) as excinfo:
            llm.get_context_window_size()
        assert "must be between 1024 and 2097152" in str(excinfo.value)
