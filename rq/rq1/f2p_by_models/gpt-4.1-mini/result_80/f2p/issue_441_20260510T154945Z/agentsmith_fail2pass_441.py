import unittest
from agentscope.message import Msg
from agentscope.models.ollama_model import OllamaChatWrapper


class TestOllamaChatWrapperRoleFix(unittest.TestCase):
    def setUp(self):
        # Prepare example inputs similar to those in format_test.py
        self.inputs = [
            Msg("system", "You are a helpful assistant", role="system"),
            [
                Msg("user", "What is the weather today?", role="user"),
                Msg("assistant", "It is sunny today", role="assistant"),
            ],
        ]

    def test_format_role_for_system_message(self):
        """
        Test that OllamaChatWrapper.format returns a list with a single dict
        where the role is 'user' (not 'system') and content includes the system
        prompt plus conversation history.

        This test should fail on the buggy code (role='system') and pass after fix
        (role='user').
        """
        model = OllamaChatWrapper(config_name="", model_name="llama3.1")

        prompt = model.format(*self.inputs)  # type: ignore[arg-type]

        # The expected output role must be 'user' per the fix and docstring
        expected_role = "user"
        self.assertIsInstance(prompt, list)
        self.assertEqual(len(prompt), 1)
        self.assertIsInstance(prompt[0], dict)
        self.assertEqual(prompt[0].get("role"), expected_role)

        # The content should contain the system message and conversation history
        content = prompt[0].get("content", "")
        self.assertIn("You are a helpful assistant", content)
        self.assertIn("user: What is the weather today?", content)
        self.assertIn("assistant: It is sunny today", content)

        # The role must not be 'system' (which is the buggy behavior)
        self.assertNotEqual(prompt[0].get("role"), "system")


if __name__ == "__main__":
    unittest.main()
