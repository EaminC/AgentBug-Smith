import tempfile
from unittest.mock import Mock, patch
from click.testing import CliRunner
from mle.cli import cli
from mle.utils.memory import LanceDBMemory


def test_memory_cli_command_exists():
    """Test that the 'memory' subcommand exists in the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ['memory', '--help'])
    assert result.exit_code == 0
    assert 'memory' in result.output


def test_memory_class_handles_missing_tables():
    """Test that LanceDBMemory methods handle missing tables gracefully.
    
    Before the fix, these methods would raise FileNotFoundError when
    trying to open a table that doesn't exist. After the fix, they
    should return empty results or True (for delete operations).
    """
    def mock_init(self, path):
        self.table_name = 'test_table'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.object(LanceDBMemory, '__init__', mock_init):
            memory = LanceDBMemory(tmpdir)
            # Set up mock client that raises FileNotFoundError (table doesn't exist)
            memory.client = Mock()
            memory.client.open_table.side_effect = FileNotFoundError("Table not found")
            # Set up mock text_embedding
            memory.text_embedding = Mock()
            memory.text_embedding.compute_source_embeddings.return_value = [[0.1, 0.2]]
            
            # Test query - should return empty list, not raise FileNotFoundError
            result = memory.query(["test query"])
            assert result == []
            
            # Test list_all_keys - should return empty list
            result = memory.list_all_keys()
            assert result == []
            
            # Test get - should return empty list
            result = memory.get("nonexistent_id")
            assert result == []
            
            # Test get_by_metadata - should return empty list
            result = memory.get_by_metadata("file", "/path/to/file")
            assert result == []
            
            # Test count - should return 0
            result = memory.count()
            assert result == 0
            
            # Test delete - should return True (idempotent)
            result = memory.delete("nonexistent_id")
            assert result == True
            
            # Test delete_by_metadata - should return True (idempotent)
            result = memory.delete_by_metadata("file", "/path/to/file")
            assert result == True
            
            # Test drop - should return True (idempotent)
            result = memory.drop()
            assert result == True
