import pytest
import asyncio
from strands.models.bedrock import BedrockModel
from strands.agent.agent import Agent
from strands.types.content import Messages
from pydantic import BaseModel


class DummyOutputModel(BaseModel):
    result: str


@pytest.mark.asyncio
async def test_structured_output_passes_system_prompt_to_bedrock_model():
    # Prepare a BedrockModel with a mock structured_output method that records the system_prompt argument
    class TestBedrockModel(BedrockModel):
        def __init__(self):
            super().__init__(
                model_id="eu.amazon.nova-lite-v1:0",
                temperature=0.0,
                top_p=0.5,
                region_name="eu-central-1",
                streaming=False,
                cache_prompt="default",
            )
            self.last_system_prompt = None

        async def structured_output(self, output_model, prompt: Messages, system_prompt=None, **kwargs):
            # Record the system_prompt argument
            self.last_system_prompt = system_prompt
            # Yield a dummy output event
            yield {"output": output_model(result="ok")}

    system_prompt_text = "You are a helpful assistant."
    prompt_text = "Please provide structured output."

    model = TestBedrockModel()
    agent = Agent(model=model, system_prompt=system_prompt_text)

    # Call structured_output on the agent, which should pass system_prompt to model.structured_output
    result = await agent.structured_output_async(DummyOutputModel, prompt_text)

    # Assert the output is as expected
    assert result.result == "ok"

    # Assert that the model's structured_output received the system_prompt
    assert model.last_system_prompt == system_prompt_text

    # Also test the synchronous structured_output method on Agent
    result_sync = agent.structured_output(DummyOutputModel, prompt_text)
    # result_sync is a coroutine, so we must await it to get the final output
    # But agent.structured_output returns the final output, not an async generator
    # Actually, agent.structured_output returns the final output by running the async generator internally
    # So we can just assert the result_sync is the same as result

    assert result_sync == result


@pytest.mark.asyncio
async def test_structured_output_fails_without_system_prompt_passed():
    # This test is designed to fail on buggy code where system_prompt is not passed to BedrockModel.structured_output
    # We simulate this by patching BedrockModel.structured_output to raise if system_prompt is None

    class TestBedrockModel(BedrockModel):
        async def structured_output(self, output_model, prompt: Messages, system_prompt=None, **kwargs):
            if system_prompt is None:
                raise ValueError("system_prompt was not passed")
            yield {"output": output_model(result="ok")}

    system_prompt_text = "System prompt required"
    prompt_text = "Test prompt"

    model = TestBedrockModel()
    agent = Agent(model=model, system_prompt=system_prompt_text)

    # The following call should NOT raise if system_prompt is passed correctly
    result = await agent.structured_output_async(DummyOutputModel, prompt_text)
    assert result.result == "ok"

    # Now test that if we call model.structured_output directly without system_prompt, it raises
    with pytest.raises(ValueError):
        # Call directly without system_prompt
        events = model.structured_output(DummyOutputModel, [{"role": "user", "content": [{"text": prompt_text}]}])
        # Consume the async generator to trigger the code
        async for _ in events:
            pass


@pytest.mark.asyncio
async def test_agent_structured_output_with_multimodal_input_and_system_prompt():
    # Test that structured_output passes system_prompt correctly when prompt is multimodal (list of dicts)
    class TestBedrockModel(BedrockModel):
        def __init__(self):
            super().__init__(
                model_id="eu.amazon.nova-lite-v1:0",
                temperature=0.0,
                top_p=0.5,
                region_name="eu-central-1",
                streaming=False,
                cache_prompt="default",
            )
            self.last_system_prompt = None
            self.last_prompt = None

        async def structured_output(self, output_model, prompt: Messages, system_prompt=None, **kwargs):
            self.last_system_prompt = system_prompt
            self.last_prompt = prompt
            yield {"output": output_model(result="ok")}

    system_prompt_text = "System prompt for multimodal test"
    prompt = [
        {"text": "Describe this image:"},
        {
            "image": {
                "format": "png",
                "source": {
                    "bytes": b"\x89PNG\r\n\x1a\n",
                },
            }
        },
    ]

    model = TestBedrockModel()
    agent = Agent(model=model, system_prompt=system_prompt_text)

    result = await agent.structured_output_async(DummyOutputModel, prompt)

    assert result.result == "ok"
    assert model.last_system_prompt == system_prompt_text
    # The prompt passed to model.structured_output should be wrapped as user role message
    assert model.last_prompt == [{"role": "user", "content": prompt}]
