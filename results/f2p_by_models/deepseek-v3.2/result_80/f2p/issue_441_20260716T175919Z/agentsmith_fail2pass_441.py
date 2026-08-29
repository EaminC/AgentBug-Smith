import unittest

import agentscope
from agentscope.message import Msg
from agentscope.models.ollama_model import OllamaChatWrapper


class OllamaFormatTest(unittest.TestCase):
    """Unit test for the format function in OllamaChatWrapper."""

    def setUp(self) -> None:
        """Init for test."""
        agentscope.init(disable_saving=True)
        self.inputs = [
            Msg("system", "You are a helpful assistant", role="system"),
            [
                Msg("user", "What is the weather today?", role="user"),
                Msg("assistant", "It is sunny today", role="assistant"),
            ],
        ]

    def test_ollama_chat_format(self) -> None:
        """Test that OllamaChatWrapper.format returns role='user' for system
        content as per docstring."""
        model = OllamaChatWrapper(
            config_name="",
            model_name="llama2",
        )

        # Expected format after fix: role='user'
        expected = [
            {
                "role": "user",
                "content": (
                    "You are a helpful assistant\n"
                    "\n"
                    "## Conversation History\n"
                    "user: What is the weather today?\n"
                    "assistant: It is sunny today"
                ),
            },
        ]

        prompt = model.format(*self.inputs)
        self.assertEqual(prompt, expected)


if __name__ == "__main__":
    unittest.main()
