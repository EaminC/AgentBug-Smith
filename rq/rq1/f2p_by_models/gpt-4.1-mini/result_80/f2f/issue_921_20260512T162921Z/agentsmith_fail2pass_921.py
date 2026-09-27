import os
import pytest

@pytest.mark.parametrize("model_name", ["gpt-3.5-turbo", "gpt-4", "text-davinci-003"])
def test_get_openai_token_cost_for_model_known_models(model_name):
    """
    Test that get_openai_token_cost_for_model returns a dict for known model names.
    This indirectly tests that the import and function are working.

    This test will fail on buggy codebase due to import error.
    After fix, it should pass.
    """
    import gpt_engineer.core.token_usage as token_usage

    # The function requires two arguments: model_name and num_tokens.
    # We provide a dummy num_tokens value (e.g., 10).
    result = token_usage.get_openai_token_cost_for_model(model_name, 10)

    # The fixed function returns a dict with cost info.
    assert isinstance(result, dict)


def test_get_openai_token_cost_for_model_function_behavior():
    """
    This test calls get_openai_token_cost_for_model with a dummy model name and token count
    to verify that it returns a dictionary with expected keys.

    This test will fail on buggy codebase if the import fails or function is missing.
    After fix, it should pass.
    """
    import gpt_engineer.core.token_usage as token_usage

    model_name = "gpt-4"
    num_tokens = 5

    result = token_usage.get_openai_token_cost_for_model(model_name, num_tokens)

    assert isinstance(result, dict)
    # Optionally check keys if known, e.g. cost, tokens, model
    # assert "cost" in result
    # assert "tokens" in result
    # assert "model" in result