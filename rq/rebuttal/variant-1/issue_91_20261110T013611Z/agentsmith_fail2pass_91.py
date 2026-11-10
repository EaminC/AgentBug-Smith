import os
import pytest
from agentscope.agents import TextToImageAgent, DialogAgent, UserAgent
from agentscope.message import Msg
from agentscope.msghub import msghub


@pytest.mark.asyncio
async def test_text_to_image_agent_receives_dialog_agent_message():
    # Setup dummy model configs with environment variables for API keys to avoid real API calls
    chat_model_config = {
        "config_name": "qwen-max",
        "model_type": "dashscope_chat",
        "model_name": "qwen-max",
        "api_key": os.getenv("OPENAI_API_KEY", "dummy_api_key")
    }
    image_model_config = {
        "config_name": "wanx-v1",
        "model_type": "dashscope_image_synthesis",
        "model_name": "wanx-v1",
        "api_key": os.getenv("OPENAI_API_KEY", "dummy_api_key")
    }

    # Initialize agentscope with both models
    import agentscope
    agentscope.init(model_configs=[chat_model_config, image_model_config])

    # Create DialogAgent with required sys_prompt and model_config_name
    agent_1 = DialogAgent(
        name="assistants",
        sys_prompt=(
            "You are tasked with narrowing down the user's description of the need to 100 words or less "
            "and relaying it to the painter for him to draw. Note that the language you generate after "
            "listening must be spoken to the painter!"
        ),
        model_config_name="qwen-max"
    )

    # Create TextToImageAgent with required args (no sys_prompt argument as it's not accepted)
    agent_2 = TextToImageAgent(
        name="painter",
        model_config_name="wanx-v1"
    )

    useragent = UserAgent()

    # Compose initial user message
    x = Msg(name="host", content='I want a fancy upscale restaurant design you know, the kind of western restaurant similar to haha')

    # Use msghub to run a group chat with both agents
    async with msghub(participants=[agent_1, agent_2]) as hub:
        # Send initial message to DialogAgent
        await agent_1(x)
        # Then call TextToImageAgent with no argument, it should get last memory message internally
        msg_from_image_agent = await agent_2()
        # UserAgent call (not strictly needed here but included for completeness)
        await useragent()

    # Assert that TextToImageAgent produced a message with content and url
    assert msg_from_image_agent is not None
    assert hasattr(msg_from_image_agent, "content")
    assert hasattr(msg_from_image_agent, "url")
    assert msg_from_image_agent.content != ""
    assert msg_from_image_agent.url is not None
    # The url attribute should be a list or similar container with at least one element (image URLs)
    assert hasattr(msg_from_image_agent.url, "__iter__")
    assert len(msg_from_image_agent.url) > 0

    # Assert that the content from DialogAgent is present in TextToImageAgent's memory
    mem = agent_2.memory.get_memory()
    assert any(isinstance(m, Msg) and m.content != "" for m in mem)

    # Also assert that the last message in TextToImageAgent's memory is the generated image message
    assert mem[-1].content == msg_from_image_agent.content
    assert mem[-1].url == msg_from_image_agent.url