import os
from unittest.mock import MagicMock, patch

import pytest
from mem0.client.main import MemoryClient
from mem0.memory.main import Memory

from crewai.agent import Agent
from crewai.crew import Crew
from crewai.memory.storage.mem0_storage import Mem0Storage
from crewai.task import Task


class MockCrew:
    def __init__(self, memory_config):
        self.memory_config = memory_config
        self.agents = [MagicMock(role="Test Agent")]


@pytest.fixture
def mock_mem0_memory():
    mock_memory = MagicMock(spec=Memory)
    return mock_memory


@pytest.fixture
def mem0_storage_with_mocked_config(mock_mem0_memory):
    with patch("mem0.memory.main.Memory.from_config", return_value=mock_mem0_memory) as mock_from_config:
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

        crew = MockCrew(
            memory_config={
                "provider": "mem0",
                "config": {"user_id": "test_user", "local_mem0_config": config},
            }
        )

        mem0_storage = Mem0Storage(type="short_term", crew=crew)
        return mem0_storage, mock_from_config, config


@pytest.fixture
def mock_mem0_memory_client():
    mock_memory = MagicMock(spec=MemoryClient)
    return mock_memory


@pytest.fixture
def mem0_storage_with_memory_client_using_config_from_crew(mock_mem0_memory_client):
    with patch.object(MemoryClient, "__new__", return_value=mock_mem0_memory_client):
        crew = MockCrew(
            memory_config={
                "provider": "mem0",
                "config": {
                    "user_id": "test_user",
                    "api_key": "ABCDEFGH",
                    "org_id": "my_org_id",
                    "project_id": "my_project_id",
                },
            }
        )

        mem0_storage = Mem0Storage(type="short_term", crew=crew)
        return mem0_storage


def test_save_method_with_memory_oss(mem0_storage_with_mocked_config):
    mem0_storage, _, _ = mem0_storage_with_mocked_config
    mem0_storage.memory.add = MagicMock()
    
    test_value = "This is a test memory"
    test_metadata = {"key": "value"}
    
    mem0_storage.save(test_value, test_metadata)
    
    mem0_storage.memory.add.assert_called_once_with(
        [{'role': 'assistant', 'content': test_value}],
        agent_id="Test_Agent",
        infer=False,
        metadata={"type": "short_term", "key": "value"},
    )


def test_save_method_with_memory_client(mem0_storage_with_memory_client_using_config_from_crew):
    mem0_storage = mem0_storage_with_memory_client_using_config_from_crew
    mem0_storage.memory.add = MagicMock()
    
    test_value = "This is a test memory"
    test_metadata = {"key": "value"}
    
    mem0_storage.save(test_value, test_metadata)
    
    mem0_storage.memory.add.assert_called_once_with(
        [{'role': 'assistant', 'content': test_value}],
        agent_id="Test_Agent",
        infer=False,
        metadata={"type": "short_term", "key": "value"},
        output_format="v1.1"
    )
