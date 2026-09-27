import pytest
from strands import Agent
from strands.models.litellm import LiteLLMModel
from strands.types.exceptions import ContextWindowOverflowException
from litellm.exceptions import ContextWindowExceededError
import unittest.mock


@pytest.mark.asyncio
async def test_litellm_context_window_overflow_exception_mapping(monkeypatch):
    """
    This test verifies that when LiteLLMModel encounters a context window overflow error
    from the litellm client, it raises the typed ContextWindowOverflowException.
    This test should fail on the buggy codebase (no mapping) and pass after the fix.
    """

    # Prepare a dummy LiteLLMModel with minimal config
    model = LiteLLMModel(
        model_id="litellm_proxy/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        client_args={
            "api_base": "http://0.0.0.0:4000",
            "api_key": "key",
        },
    )

    # Define an async generator that raises ContextWindowExceededError on iteration
    async def raise_context_window_error(*args, **kwargs):
        raise ContextWindowExceededError(
            message="Input too long for model context window",
            model=model.get_config()["model_id"],
            llm_provider="litellm",
        )

    # Patch litellm.acompletion to raise the ContextWindowExceededError
    monkeypatch.setattr("litellm.acompletion", raise_context_window_error)

    # Compose a very large input to simulate overflow (content irrelevant since patched)
    large_input = [{"role": "user", "content": [{"text": "Hi" * 1000000}]}]

    # The Agent wraps the model and calls model.stream internally
    agent = Agent(model=model)

    # We expect the agent call to raise ContextWindowOverflowException (not raw litellm error)
    with pytest.raises(ContextWindowOverflowException):
        # Agent is async callable, so await the call
        await agent(large_input)


@pytest.mark.asyncio
async def test_litellm_structured_output_context_window_overflow(monkeypatch):
    """
    This test verifies that the structured_output method also maps the context window overflow
    error to ContextWindowOverflowException.
    """

    model = LiteLLMModel(
        model_id="litellm_proxy/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        client_args={
            "api_base": "http://0.0.0.0:4000",
            "api_key": "key",
        },
    )

    # Patch supports_response_schema to True to allow structured_output call
    monkeypatch.setattr("strands.models.litellm.supports_response_schema", lambda model_id: True)

    # Patch litellm.acompletion to raise ContextWindowExceededError
    async def raise_context_window_error(*args, **kwargs):
        raise ContextWindowExceededError(
            message="Input too long for model context window",
            model=model.get_config()["model_id"],
            llm_provider="litellm",
        )

    monkeypatch.setattr("litellm.acompletion", raise_context_window_error)

    # Define a dummy Pydantic model for output
    import pydantic

    class DummyOutput(pydantic.BaseModel):
        foo: str

    # Compose a prompt input (content irrelevant since patched)
    prompt = [{"role": "user", "content": [{"text": "test"}]}]

    # Expect ContextWindowOverflowException when calling structured_output
    with pytest.raises(ContextWindowOverflowException):
        async for _ in model.structured_output(DummyOutput, prompt):
            pass
