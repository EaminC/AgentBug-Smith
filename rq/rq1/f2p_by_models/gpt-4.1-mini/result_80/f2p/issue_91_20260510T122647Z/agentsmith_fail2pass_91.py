import pytest
from unittest.mock import patch
import agentscope
from agentscope.agents import TextToImageAgent, DialogAgent, UserAgent
from agentscope.message import Msg
from agentscope.msghub import msghub


def test_text_to_image_agent_receives_dialogagent_message():
    """
    This test verifies that when DialogAgent and TextToImageAgent participate in a msghub group chat,
    the TextToImageAgent can receive and process the message content relayed by DialogAgent.

    The buggy code fails because TextToImageAgent.reply() receives None instead of a message,
    causing an error when accessing x.content. The fix ensures that if no input is given,
    TextToImageAgent.reply() fetches the last message from memory.

    This test mocks the internal model calls to avoid real API calls and to produce predictable outputs.
    """

    class DummyChatModelResponse:
        def __init__(self):
            self.text = "Narrowed description for painter"
            self.image_urls = ["http://dummyimage.com/fake.png"]

    class DummyImageModelResponse:
        def __init__(self):
            self.image_urls = ["http://dummyimage.com/fake.png"]

    # Patch the internal model calls inside the agentscope.models.dashscope_model.DashScopeChatWrapper
    # and DashScopeImageSynthesisWrapper to avoid real network calls.
    # The actual classes used in agentscope are DashScopeChatWrapper and DashScopeImageSynthesisWrapper,
    # not DashScopeChatModel or DashScopeImageSynthesisModel.
    with patch("agentscope.models.dashscope_model.DashScopeChatWrapper.__call__", return_value=DummyChatModelResponse()), \
         patch("agentscope.models.dashscope_model.DashScopeImageSynthesisWrapper.__call__", return_value=DummyImageModelResponse()):

        # Initialize agents with dummy model configs
        agent_to_chat = agentscope.init(model_configs=[
            {
                "config_name": "qwen-max",
                "model_type": "dashscope_chat",
                "model_name": "qwen-max",
                "api_key": "dummy_api_key"
            }
        ])
        agent_to_image = agentscope.init(model_configs=[
            {
                "config_name": "wanx-v1",
                "model_type": "dashscope_image_synthesis",
                "model_name": "wanx-v1",
                "api_key": "dummy_api_key"
            }
        ])

        agent_1 = DialogAgent(
            name="assistants",
            sys_prompt="You are tasked with narrowing down the user's description of the need to 100 words or less and relaying it to the painter for him to draw. Note that the language you generate after listening must be spoken to the painter!",
            model_config_name="qwen-max"
        )
        # Note: TextToImageAgent no longer accepts sys_prompt argument after fix
        agent_2 = TextToImageAgent(
            name="painter",
            model_config_name="wanx-v1"
        )
        useragent = UserAgent()

        # Create initial message from user
        x = Msg(name="host", content='I want a fancy upscale restaurant design you know, the kind of western restaurant similar to haha')

        # Use msghub to simulate group chat between agents
        with msghub(participants=[agent_1, agent_2]) as hub:
            # DialogAgent receives user message and processes it
            agent_1(x)

            # TextToImageAgent should receive the message relayed by DialogAgent from memory automatically
            # The buggy code fails here because agent_2() receives None
            # The fix makes agent_2() fetch last message from memory if no input is given
            msg = agent_2()

            # Assert that the returned message is a Msg instance with expected content and url
            assert msg is not None
            assert hasattr(msg, "content")
            assert hasattr(msg, "url")
            assert msg.content == "This is the generated image "
            assert isinstance(msg.url, list)
            assert len(msg.url) > 0
            assert msg.url[0] == "http://dummyimage.com/fake.png"
