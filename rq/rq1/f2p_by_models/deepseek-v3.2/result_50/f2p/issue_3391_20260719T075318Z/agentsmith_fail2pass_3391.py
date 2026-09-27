from unittest.mock import MagicMock, patch

import pytest
from mem0.client.main import MemoryClient
from mem0.memory.main import Memory

from crewai.memory.storage.mem0_storage import Mem0Storage


class MockCrew:
    def __init__(self):
        self.agents = [MagicMock(role="Test Agent")]


@pytest.fixture
def mock_mem0_memory():
    return MagicMock(spec=Memory)


@pytest.fixture
def mem0_storage_with_mocked_config(mock_mem0_memory):
    with patch("mem0.memory.main.Memory.from_config", return_value=mock_mem0_memory):
        config = {
            "vector_store": {
                "provider": "mock_vector_store",
                "config": {"host": "localhost", "port": 6333},
            },
            "llm": {
                "provider": "mock_llm",
                "config": {"api_key": "mock-api-key", "model": "mock-model"},
            },
            "embedder": {
                "provider": "mock_embedder",
                "config": {"api_key": "mock-api-key", "model": "mock-model"},
            },
            "graph_store": {
                "provider": "mock_graph_store",
                "config": {
                    "url": "mock-url",
                    "username": "mock-user",
                    "password": "mock-password",
                },
            },
            "history_db_path": "/mock/path",
            "version": "test-version",
            "custom_fact_extraction_prompt": "mock prompt 1",
            "custom_update_memory_prompt": "mock prompt 2",
        }
        crew = MockCrew()
        embedder_config = {
            "user_id": "test_user",
            "local_mem0_config": config,
            "run_id": "my_run_id",
            "includes": "include1",
            "excludes": "exclude1",
            "infer": True,
        }
        mem0_storage = Mem0Storage(type="short_term", crew=crew, config=embedder_config)
        return mem0_storage, config


def test_save_with_messages_metadata_extracts_user_and_assistant(mem0_storage_with_mocked_config):
    """
    Test that the save method correctly extracts the last user message
    and assistant final answer from the messages metadata, and does not
    include the full messages in the metadata passed to memory.add.
    """
    mem0_storage, _ = mem0_storage_with_mocked_config
    mem0_storage.memory.add = MagicMock()

    # Simulate a long conversation that would hit the metadata limit if not trimmed
    test_value = "Short assistant response"
    metadata = {
        "description": "Respond to user conversation. User message: What do you know about me?",
        "messages": [
            {
                "role": "system",
                "content": "You are a friendly chatbot assistant. This is a very long system prompt that would exceed the metadata limit if included in full. " * 50,
            },
            {
                "role": "user",
                "content": "What do you know about me?",
            },
            {
                "role": "assistant",
                "content": "I now can give a great answer  Final Answer: Hi there! I'm a friendly chatbot assistant. I know you're asking about what I know about you. From our previous conversations, I have gathered some information about you. Let me share it with you!",
            },
        ],
        "agent": "Friendly chatbot assistant",
    }

    mem0_storage.save(test_value, metadata)

    # Expected behavior after fix:
    # - metadata should not contain 'messages'
    # - conversations list should contain the extracted user message and assistant final answer
    expected_conversations = [
        {"role": "user", "content": "What do you know about me?"},
        {
            "role": "assistant",
            "content": "Hi there! I'm a friendly chatbot assistant. I know you're asking about what I know about you. From our previous conversations, I have gathered some information about you. Let me share it with you!",
        },
    ]
    expected_metadata = {
        "type": "short_term",
        "description": "Respond to user conversation. User message: What do you know about me?",
        "agent": "Friendly chatbot assistant",
    }

    mem0_storage.memory.add.assert_called_once_with(
        expected_conversations,
        infer=True,
        metadata=expected_metadata,
        run_id="my_run_id",
        user_id="test_user",
        agent_id="Test_Agent",
    )
