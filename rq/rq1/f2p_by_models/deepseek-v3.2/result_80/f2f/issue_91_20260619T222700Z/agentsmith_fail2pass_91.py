import unittest
from unittest.mock import patch, MagicMock
import pytest
from agentscope.agents import TextToImageAgent, DialogAgent, UserAgent
from agentscope.message import Msg
from agentscope.msghub import msghub


class TestTextToImageAgentMsghubInteraction(unittest.TestCase):
    def setUp(self) -> None:
        # Mock the model configuration loading
        self.model_configs_patch = patch.dict(
            "agentscope._runtime._config.model_configs",
            {
                "qwen-max": {
                    "config_name": "qwen-max",
                    "model_type": "dashscope_chat",
                    "model_name": "qwen-max",
                    "api_key": "test_key",
                },
                "wanx-v1": {
                    "config_name": "wanx-v1",
                    "model_type": "dashscope_image_synthesis",
                    "model_name": "wanx-v1",
                    "api_key": "test_key",
                },
            },
            clear=True,
        )
        self.model_configs_patch.start()

        # Mock the model instantiation for DialogAgent (chat model)
        self.chat_model_mock = MagicMock()
        self.chat_model_mock.return_value = Msg(name="assistants", content="Narrowed description for painter")
        
        # Mock the actual model wrapper class
        self.chat_model_patch = patch(
            "agentscope.agents.dialog_agent.DashScopeChatWrapper",
            return_value=self.chat_model_mock,
        )
        self.chat_model_patch.start()

        # Mock the model instantiation for TextToImageAgent (image model)
        self.image_model_mock = MagicMock()
        self.image_model_mock.image_urls = ["http://example.com/image.png"]
        
        # Mock the actual model wrapper class
        self.image_model_patch = patch(
            "agentscope.agents.text_to_image_agent.DashScopeImageSynthesisWrapper",
            return_value=self.image_model_mock,
        )
        self.image_model_patch.start()

    def tearDown(self) -> None:
        self.model_configs_patch.stop()
        self.chat_model_patch.stop()
        self.image_model_patch.stop()

    def test_text_to_image_agent_receives_message_in_msghub(self):
        """Test that TextToImageAgent can receive the last message from memory when called without arguments in msghub."""
        # Create agents with mocked models
        agent1 = DialogAgent(
            name="assistants",
            sys_prompt="You are an assistant.",
            model_config_name="qwen-max",
        )
        agent2 = TextToImageAgent(
            name="painter",
            model_config_name="wanx-v1",
        )
        user = UserAgent()

        # Initial message from user
        x = Msg(name="host", content="I want a fancy restaurant design")

        with msghub(participants=[agent1, agent2]):
            # agent1 processes the user message and replies
            reply1 = agent1(x)
            # agent2 is called without arguments; in buggy version, x is None inside reply()
            # In fixed version, agent2 should retrieve the last message from memory (which is reply1)
            reply2 = agent2()
            # User agent step (optional)
            user()

        # Verify that agent2's model was called with the content from agent1's reply
        # The buggy version would have called self.model(None.content) causing AttributeError
        # The fixed version should call self.model with the content of the last memory message
        self.image_model_mock.assert_called_once()
        call_args = self.image_model_mock.call_args
        # The model is called with the content string
        self.assertIsInstance(call_args[0][0], str)
        # The content should be from agent1's reply
        self.assertEqual(call_args[0][0], reply1["content"])

    def test_text_to_image_agent_with_explicit_message(self):
        """Test that TextToImageAgent works when an explicit message is passed."""
        agent = TextToImageAgent(
            name="painter",
            model_config_name="wanx-v1",
        )
        msg = Msg(name="user", content="Draw a cat")
        # This should work in both buggy and fixed versions
        reply = agent(msg)
        self.image_model_mock.assert_called_once_with("Draw a cat")
        self.assertIn("url", reply)
        self.assertEqual(reply["url"], ["http://example.com/image.png"])

    def test_text_to_image_agent_with_empty_memory(self):
        """Test that TextToImageAgent returns empty dict when no memory and no input."""
        agent = TextToImageAgent(
            name="painter",
            model_config_name="wanx-v1",
            use_memory=False,
        )
        # In buggy version, this would try to access x.content when x is None
        # In fixed version, it should return {} because memory is empty
        reply = agent()
        self.assertEqual(reply, {})
        self.image_model_mock.assert_not_called()

    def test_text_to_image_agent_sys_prompt_removed(self):
        """Test that TextToImageAgent no longer requires sys_prompt argument."""
        # In buggy version, constructor requires sys_prompt
        # In fixed version, sys_prompt is removed from constructor
        # This test verifies the constructor signature change
        agent = TextToImageAgent(
            name="painter",
            model_config_name="wanx-v1",
        )
        # Should not raise TypeError about missing sys_prompt
        self.assertEqual(agent.name, "painter")
        # The sys_prompt should be empty string internally
        self.assertEqual(agent.sys_prompt, "")


# Add pytest-compatible test functions for better compatibility
def test_text_to_image_agent_basic():
    """Basic test for TextToImageAgent functionality."""
    with patch.dict(
        "agentscope._runtime._config.model_configs",
        {
            "wanx-v1": {
                "config_name": "wanx-v1",
                "model_type": "dashscope_image_synthesis",
                "model_name": "wanx-v1",
                "api_key": "test_key",
            },
        },
        clear=True,
    ):
        with patch(
            "agentscope.agents.text_to_image_agent.DashScopeImageSynthesisWrapper",
            return_value=MagicMock(image_urls=["http://example.com/image.png"])
        ):
            agent = TextToImageAgent(
                name="painter",
                model_config_name="wanx-v1",
            )
            msg = Msg(name="user", content="Draw a cat")
            reply = agent(msg)
            assert "url" in reply
            assert reply["url"] == ["http://example.com/image.png"]


if __name__ == "__main__":
    unittest.main()