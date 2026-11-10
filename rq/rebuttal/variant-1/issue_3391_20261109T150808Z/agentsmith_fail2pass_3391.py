import pytest
from unittest.mock import MagicMock, patch
from crewai.memory.storage.mem0_storage import Mem0Storage


class DummyMemory:
    def __init__(self):
        self.add_calls = []

    def add(self, conversations, **kwargs):
        self.add_calls.append((conversations, kwargs))


def test_save_with_large_metadata_and_messages():
    """
    Test that Mem0Storage.save correctly handles large metadata with messages,
    extracting user and assistant messages and passing them properly to memory.add.
    This should not fail even if metadata length is large.
    """

    # Create a large user message and assistant message to simulate >2000 chars metadata
    large_user_message = "User message: " + "A" * 2100
    large_assistant_message = "Final Answer: " + "B" * 2100

    messages = [
        {"role": "system", "content": "System prompt content"},
        {"role": "user", "content": large_user_message},
        {"role": "assistant", "content": large_assistant_message},
    ]

    metadata = {
        "description": "Test large metadata with messages",
        "messages": messages,
        "agent": "Test Agent",
    }

    # Patch the Memory class to use our DummyMemory to capture calls
    with patch("mem0.memory.main.Memory.from_config") as mock_from_config:
        dummy_memory = DummyMemory()
        mock_from_config.return_value = dummy_memory

        # Setup config with user_id, run_id, etc.
        config = {
            "user_id": "test_user",
            "run_id": "test_run",
        }

        mem0_storage = Mem0Storage(type="short_term", config=config)
        mem0_storage.memory = dummy_memory  # Override with dummy memory

        # Call save with dummy value and large metadata
        mem0_storage.save("irrelevant_value", metadata.copy())

        # There should be exactly one call to add
        assert len(dummy_memory.add_calls) == 1

        conversations, kwargs = dummy_memory.add_calls[0]

        # The conversations should contain exactly two messages: user and assistant extracted
        assert isinstance(conversations, list)
        assert len(conversations) == 2

        # The user message content should be the large_user_message content stripped of prefix
        expected_user_content = "A" * 2100
        # The code extracts user message after "User message:" prefix
        assert conversations[0]["role"] == "user"
        assert conversations[0]["content"] == expected_user_content

        # The assistant message content should be the large_assistant_message content stripped of prefix
        expected_assistant_content = "B" * 2100
        # The code extracts assistant message after "Final Answer:" prefix
        assert conversations[1]["role"] == "assistant"
        assert conversations[1]["content"] == expected_assistant_content

        # Check that metadata in kwargs contains the original keys except 'messages' removed and type added
        # The original metadata keys except 'messages' are 'description' and 'agent'
        expected_metadata = {
            "type": "short_term",
            "description": "Test large metadata with messages",
            "agent": "Test Agent",
        }
        assert kwargs.get("metadata") == expected_metadata

        # Check that run_id and user_id are passed correctly
        assert kwargs.get("run_id") == "test_run"
        assert kwargs.get("user_id") == "test_user"

        # infer should be True by default
        assert kwargs.get("infer") is True

        # agent_id should be empty string because no agent_id in config and no crew agents
        # The default _get_agent_name returns empty string if no crew or agents
        assert kwargs.get("agent_id") == "" or kwargs.get("agent_id") is None


# This test file only contains the above test to verify the fix for large metadata handling in Mem0Storage.save.
# It should fail on buggy code (due to metadata length) and pass on fixed code.
