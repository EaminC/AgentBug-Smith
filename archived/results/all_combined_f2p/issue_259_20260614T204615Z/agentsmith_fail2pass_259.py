import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import pytest

def test_lancedb_memory_class_exists():
    """Test that LanceDBMemory class exists in mle.utils.memory"""
    from mle.utils.memory import LanceDBMemory
    assert LanceDBMemory is not None

def test_lancedb_memory_has_required_methods():
    """Test that LanceDBMemory has all required methods"""
    from mle.utils.memory import LanceDBMemory
    
    required_methods = ['add', 'query', 'delete', 'drop', 'count', 'reset']
    for method in required_methods:
        assert hasattr(LanceDBMemory, method), f"LanceDBMemory missing method: {method}"

def test_chromadb_memory_class_exists():
    """Test that ChromaDBMemory class exists (renamed from Memory)"""
    from mle.utils.memory import ChromaDBMemory
    assert ChromaDBMemory is not None

def test_memory_not_imported_in_cli():
    """Test that Memory is not imported in cli.py"""
    with open('mle/cli.py', 'r') as f:
        content = f.read()
    
    # Check that the old import is removed
    assert 'from mle.utils import Memory' not in content, "Old Memory import should be removed from cli.py"

def test_lancedb_memory_initialization():
    """Test LanceDBMemory initialization with mocked dependencies"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        
        assert memory.db_name == '.mle'
        assert memory.table_name == 'memory'
        mock_lancedb.connect.assert_called_once_with(uri='.mle')

def test_lancedb_memory_add_method():
    """Test LanceDBMemory.add method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_embedding.compute_source_embeddings.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        mock_client.table_names.return_value = []
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        ids = memory.add(texts=["test text 1", "test text 2"])
        
        assert len(ids) == 2
        mock_embedding.compute_source_embeddings.assert_called_once()
        mock_client.create_table.assert_called_once()

def test_lancedb_memory_query_method():
    """Test LanceDBMemory.query method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_embedding.compute_source_embeddings.return_value = [[0.1, 0.2]]
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        mock_table = MagicMock()
        mock_search_result = MagicMock()
        mock_search_result.limit.return_value = mock_search_result
        mock_search_result.to_list.return_value = [{"text": "result", "id": "1"}]
        mock_table.search.return_value = mock_search_result
        mock_client.open_table.return_value = mock_table
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        results = memory.query(query_texts=["query text"])
        
        assert len(results) == 1
        assert len(results[0]) == 1
        assert results[0][0]["text"] == "result"

def test_lancedb_memory_delete_method():
    """Test LanceDBMemory.delete method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        mock_table = MagicMock()
        mock_table.delete.return_value = True
        mock_client.open_table.return_value = mock_table
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        result = memory.delete(record_id="test-id")
        
        assert result is True
        mock_table.delete.assert_called_once_with("id = 'test-id'")

def test_lancedb_memory_drop_method():
    """Test LanceDBMemory.drop method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        mock_client.drop_table.return_value = True
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        result = memory.drop()
        
        assert result is True
        mock_client.drop_table.assert_called_once_with('memory')

def test_lancedb_memory_count_method():
    """Test LanceDBMemory.count method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        mock_table = MagicMock()
        mock_table.count_rows.return_value = 42
        mock_client.open_table.return_value = mock_table
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        count = memory.count()
        
        assert count == 42
        mock_table.count_rows.assert_called_once()

def test_lancedb_memory_reset_method():
    """Test LanceDBMemory.reset method"""
    with patch('mle.utils.memory.lancedb') as mock_lancedb, \
         patch('mle.utils.memory.get_registry') as mock_get_registry, \
         patch('mle.utils.memory.get_config') as mock_get_config:
        
        # Setup mocks
        mock_client = MagicMock()
        mock_lancedb.connect.return_value = mock_client
        mock_client.drop_table.return_value = True
        
        mock_registry = MagicMock()
        mock_openai = MagicMock()
        mock_registry.get.return_value = mock_openai
        mock_get_registry.return_value = mock_registry
        
        mock_embedding = MagicMock()
        mock_openai.create.return_value = mock_embedding
        
        mock_get_config.return_value = {
            "platform": "OpenAI",
            "api_key": "test-key"
        }
        
        from mle.utils.memory import LanceDBMemory
        
        memory = LanceDBMemory(project_path="/tmp/test")
        memory.reset()
        
        mock_client.drop_table.assert_called_once_with('memory')
