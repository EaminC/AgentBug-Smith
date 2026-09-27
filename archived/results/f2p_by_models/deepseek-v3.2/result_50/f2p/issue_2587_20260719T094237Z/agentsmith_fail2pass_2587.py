from unittest.mock import MagicMock, patch

import pytest

from crewai.memory.storage.mem0_storage import Mem0Storage


class MockCrew:
    def __init__(self, memory_config):
        self.memory_config = memory_config


def test_mem0_local_config_is_used_in_memory_from_config():
    """Ensure that when a local_mem0_config is provided,
    Memory.from_config is called with that config, not the global config."""

    local_config = {
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
            "config": {"user_id": "test_user", "local_mem0_config": local_config},
        }
    )

    with patch("mem0.memory.main.Memory.from_config", return_value=MagicMock()) as mock_from_config:
        _ = Mem0Storage(type="short_term", crew=crew)

        # Buggy code calls Memory.from_config(config) where config is the global
        # config parameter (None in this case). Fixed code calls
        # Memory.from_config(mem0_local_config) which is local_config.
        mock_from_config.assert_called_once_with(local_config)
