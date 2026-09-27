import os
import pytest
import asyncio
from src.crewai.llm import LLM


class DummyLlamaAPIClient:
    async def acall(self, prompt_or_messages):
        # Return a dummy response mimicking Llama API output
        if isinstance(prompt_or_messages, list):
            # Assume message list input
            return {"choices": [{"message": {"content": "Hello from Llama API (message list)"}}]}
        elif isinstance(prompt_or_messages, str):
            # Plain prompt string input
            if "JSON" in prompt_or_messages:
                # Return a structured JSON-like response
                return {"choices": [{"message": {"content": '{"greeting": "hello"}'}}]}
            return {"choices": [{"message": {"content": "Hello from Llama API"}}]}
        else:
            return {"choices": [{"message": {"content": "Hello from Llama API (unknown input)"}}]}


@pytest.mark.asyncio
async def test_llm_call_with_llama_api():
    """
    Test that the LLM class supports Llama API integration correctly.

    This test will fail on the buggy codebase where Llama API support is missing or broken,
    and pass after the fix that integrates Llama API support in LiteLLM and crewAI.
    """

    # Instantiate LLM with model and provider set to litellm (which should support Llama API)
    llm = LLM(model="llama-2-7b-chat", provider="litellm")

    # Replace the internal client with our dummy client that returns a fixed response
    llm._client = DummyLlamaAPIClient()

    # Compose a simple prompt
    prompt = "Say hello"

    # Call the LLM with the prompt using the async interface
    # The fixed codebase should have 'call' method; buggy does not have 'acall'.
    # Await the coroutine returned by call()
    response = await llm.call(prompt)

    # Assert the response contains expected dummy content
    assert "choices" in response
    assert response["choices"][0]["message"]["content"].startswith("Hello from Llama API")


@pytest.mark.asyncio
async def test_llm_call_with_llama_api_message_list():
    """
    Test that the LLM class supports Llama API calls with message list input.

    This test will fail on the buggy codebase and pass after the fix.
    """

    llm = LLM(model="llama-2-7b-chat", provider="litellm")
    llm._client = DummyLlamaAPIClient()

    messages = [{"role": "user", "content": "Hello, Llama API!"}]

    response = await llm.call(messages)

    assert "choices" in response
    assert response["choices"][0]["message"]["content"].startswith("Hello from Llama API (message list)")


@pytest.mark.asyncio
async def test_llm_call_with_llama_api_structured():
    """
    Test that the LLM class returns expected structured output from Llama API.

    This test will fail on buggy codebase and pass after fix.
    """

    llm = LLM(model="llama-2-7b-chat", provider="litellm")
    llm._client = DummyLlamaAPIClient()

    prompt = "Provide a JSON object with key 'greeting' and value 'hello'"

    response = await llm.call(prompt)

    assert "choices" in response
    content = response["choices"][0]["message"]["content"]
    assert content.startswith("{") and content.endswith("}")
    assert '"greeting": "hello"' in content