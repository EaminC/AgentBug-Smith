import unittest
import agentscope
from agentscope.message import Msg
from agentscope.models import OllamaChatWrapper


class TestOllamaChatWrapperRole(unittest.TestCase):
    """Test that OllamaChatWrapper.format sets role to 'user'."""

    def setUp(self) -> None:
        """Initialize agentscope."""
        agentscope.init(disable_saving=True)

    def test_ollama_chat_format_role_is_user(self) -> None:
        """Verify format() returns role='user' as per docstring."""
        model = OllamaChatWrapper(
            config_name="",
            model_name="llama3.1",
        )

        inputs = [
            Msg("system", "You are a helpful assistant", role="system"),
            [
                Msg("user", "What is the weather today?", role="user"),
                Msg("assistant", "It is sunny today", role="assistant"),
            ],
        ]

        prompt = model.format(*inputs)

        # The bug was that role was incorrectly set to "system" instead of "user"
        self.assertEqual(len(prompt), 1)
        self.assertEqual(prompt[0]["role"], "user")
        self.assertIn("You are a helpful assistant", prompt[0]["content"])
        self.assertIn("## Conversation History", prompt[0]["content"])
        self.assertIn("user: What is the weather today?", prompt[0]["content"])
        self.assertIn("assistant: It is sunny today", prompt[0]["content"])


if __name__ == "__main__":
    unittest.main()
