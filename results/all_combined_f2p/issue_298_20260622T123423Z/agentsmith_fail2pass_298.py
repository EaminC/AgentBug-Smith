import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
import pytest
from mle.utils.memory import Mem0


class TestMem0:
    def test_mem0_add_with_metadata(self):
        """Test that Mem0.add correctly passes metadata to the underlying client."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient, \
             patch('mle.utils.memory.Memory') as MockMemory:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            mem = Mem0(token="fake_token")
            
            messages = [{"role": "user", "content": "test"}]
            metadata = {"session": "debug", "task": "fix bug"}
            
            mem.add(messages, metadata=metadata)
            
            mock_client.add.assert_called_once_with(
                messages,
                metadata=metadata,
                prompt=None,
                infer=False,
                agent_id="default"
            )

    def test_mem0_add_without_token_uses_local_memory(self):
        """Test that Mem0 initializes with local Memory when no token provided."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient, \
             patch('mle.utils.memory.Memory') as MockMemory:
            mock_memory = MagicMock()
            MockMemory.return_value = mock_memory
            
            mem = Mem0()
            
            MockMemoryClient.assert_not_called()
            MockMemory.assert_called_once()
            assert mem.client == mock_memory

    def test_mem0_query_calls_search_with_correct_params(self):
        """Test that Mem0.query calls client.search with proper arguments."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            mem.query("test query", n_results=10)
            
            mock_client.search.assert_called_once_with(
                agent_id="default",
                query_text="test query",
                limit=10
            )

    def test_mem0_get_all_with_filters(self):
        """Test that Mem0.get_all passes filters to client.get_all."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            filters = {"type": "debug"}
            mem.get_all(filters=filters, n_results=50)
            
            mock_client.get_all.assert_called_once_with(
                agent_id="default",
                filters=filters,
                limit=50
            )

    def test_mem0_reset(self):
        """Test that Mem0.reset calls client.reset with agent_id."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            mem.reset()
            
            mock_client.reset.assert_called_once_with(agent_id="default")

    def test_mem0_agent_id_propagation(self):
        """Test that custom agent_id is used in all client calls."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token", agent_id="custom_agent")
            
            mem.add([{"role": "user", "content": "test"}])
            mock_client.add.assert_called_once_with(
                [{"role": "user", "content": "test"}],
                metadata=None,
                prompt=None,
                infer=False,
                agent_id="custom_agent"
            )
            
            mock_client.reset_mock()
            mem.query("test")
            mock_client.search.assert_called_once_with(
                agent_id="custom_agent",
                query_text="test",
                limit=5
            )
            
            mock_client.reset_mock()
            mem.get_all()
            mock_client.get_all.assert_called_once_with(
                agent_id="custom_agent",
                filters=None,
                limit=100
            )
            
            mock_client.reset_mock()
            mem.reset()
            mock_client.reset.assert_called_once_with(agent_id="custom_agent")

    def test_mem0_add_with_prompt_and_infer(self):
        """Test that Mem0.add passes prompt and infer parameters correctly."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            messages = [{"role": "user", "content": "test"}]
            
            mem.add(messages, prompt="Extract key facts", infer=True)
            
            mock_client.add.assert_called_once_with(
                messages,
                metadata=None,
                prompt="Extract key facts",
                infer=True,
                agent_id="default"
            )

    def test_mem0_query_default_n_results(self):
        """Test that Mem0.query uses default n_results=5 when not specified."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            mem.query("test query")
            
            mock_client.search.assert_called_once_with(
                agent_id="default",
                query_text="test query",
                limit=5
            )

    def test_mem0_get_all_default_n_results(self):
        """Test that Mem0.get_all uses default n_results=100 when not specified."""
        with patch('mle.utils.memory.MemoryClient') as MockMemoryClient:
            mock_client = MagicMock()
            MockMemoryClient.return_value = mock_client
            
            mem = Mem0(token="fake_token")
            mem.get_all()
            
            mock_client.get_all.assert_called_once_with(
                agent_id="default",
                filters=None,
                limit=100
            )
