# tests/formatter_dashscope_test.py
import unittest
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg


class TestDashScopeChatFormatter(unittest.TestCase):
    """Test suite for DashScopeChatFormatter to verify proper message formatting."""
    
    def setUp(self):
        self.formatter = DashScopeChatFormatter()
    
    def test_format_chat_prompt_with_system_message(self):
        """Test that system messages are correctly formatted for DashScope API.
        
        This test verifies the fix for the bug where system messages were
        incorrectly formatted or omitted in the DashScope chat formatter.
        """
        messages = [
            Msg(name="system", content="You are a helpful coding assistant.", role="system"),
            Msg(name="user", content="Write a Python function to sort a list.", role="user")
        ]
        
        result = self.formatter.format_chat_prompt(messages)
        
        # Verify the result contains the messages key
        self.assertIn("messages", result)
        self.assertIsInstance(result["messages"], list)
        self.assertEqual(len(result["messages"]), 2)
        
        # Verify system message is preserved with correct role
        system_msg = result["messages"][0]
        self.assertEqual(system_msg["role"], "system")
        self.assertEqual(system_msg["content"], "You are a helpful coding assistant.")
        
        # Verify user message follows
        user_msg = result["messages"][1]
        self.assertEqual(user_msg["role"], "user")
        self.assertEqual(user_msg["content"], "Write a Python function to sort a list.")
    
    def test_format_chat_prompt_multi_turn_conversation(self):
        """Test formatting of multi-turn conversations."""
        messages = [
            Msg(name="user", content="Hello", role="user"),
            Msg(name="assistant", content="Hi! How can I help?", role="assistant"),
            Msg(name="user", content="What's the weather?", role="user")
        ]
        
        result = self.formatter.format_chat_prompt(messages)
        
        self.assertEqual(len(result["messages"]), 3)
        self.assertEqual(result["messages"][0]["role"], "user")
        self.assertEqual(result["messages"][1]["role"], "assistant")
        self.assertEqual(result["messages"][2]["role"], "user")
    
    def test_format_chat_prompt_empty_messages(self):
        """Test handling of empty message list."""
        result = self.formatter.format_chat_prompt([])
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 0)


if __name__ == "__main__":
    unittest.main()