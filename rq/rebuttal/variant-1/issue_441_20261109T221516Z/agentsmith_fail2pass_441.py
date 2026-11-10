import unittest

import agentscope
from agentscope.message import Msg
from agentscope.models import OllamaChatWrapper


class OllamaChatWrapperRoleTest(unittest.TestCase):
    """Test that OllamaChatWrapper.format produces correct role for system message."""

    def setUp(self) -> None:
        agentscope.init(disable_saving=True)
        # Prepare inputs similar to those used in format_test.py
        self.inputs = [
            Msg("system", "You are a helpful assistant", role="system"),
            [
                Msg("user", "What is the weather today?", role="user"),
                Msg("assistant", "It is sunny today", role="assistant"),
            ],
        ]

    def test_ollama_chat_format_role(self) -> None:
        """Test that the role in the formatted prompt is 'user' not 'system' as per fix."""
        model = OllamaChatWrapper(config_name="", model_name="llama2")

        prompt = model.format(*self.inputs)  # type: ignore[arg-type]

        # The buggy code sets role to "system", the fix sets it to "user"
        # So before fix, this test fails because role is "system"
        # After fix, role is "user" and test passes

        self.assertIsInstance(prompt, list)
        self.assertEqual(len(prompt), 1)
        message = prompt[0]
        self.assertIsInstance(message, dict)
        self.assertIn("role", message)
        self.assertIn("content", message)

        # Assert role is "user" as per the fix and docstring
        self.assertEqual(message["role"], "user")

        # Assert content includes the system prompt and conversation history
        content = message["content"]
        self.assertIn("You are a helpful assistant", content)
        self.assertIn("user: What is the weather today?", content)
        self.assertIn("assistant: It is sunny today", content)


if __name__ == "__main__":
    unittest.main()
