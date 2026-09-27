import openai
import pytest
from ai import AI


def test_fallback_to_gpt35_when_gpt4_unavailable(monkeypatch):
    """
    Test that AI falls back to gpt-3.5-turbo when gpt-4 is not available.
    
    This test verifies the fix for issue #9 - ensuring the AI class gracefully
    falls back to gpt-3.5-turbo when the API key doesn't have access to gpt-4.
    """
    def mock_retrieve(model):
        raise openai.error.InvalidRequestError(
            "The model 'gpt-4' does not exist or you do not have access to it.",
            "model"
        )
    
    monkeypatch.setattr(openai.Model, "retrieve", mock_retrieve)
    
    ai = AI(model="gpt-4")
    
    assert ai.kwargs['model'] == 'gpt-3.5-turbo'
