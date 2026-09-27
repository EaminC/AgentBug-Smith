import os
import tempfile
import shutil
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from mle.cli import cli
from mle.utils.memory import LanceDBMemory
from mle.utils.chunk import CodeChunker

def test_memory_cli_add_rm_update():
    """
    Test the new `mle memory` CLI commands: --add, --rm, --update.
    The buggy code may have issues with missing _open_table method or incorrect handling.
    This test should fail before the patch and pass after.
    """
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy Python file
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write("print('hello')")
        # Create a subdirectory with another file
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir)
        test_file2 = os.path.join(subdir, "test2.py")
        with open(test_file2, "w") as f:
            f.write("def foo(): pass")

        # Mock the LanceDBMemory to avoid real database operations
        # We need to mock the internal methods that are called by the CLI.
        # The bug is in the memory module's _open_table and related methods.
        # We'll mock the entire LanceDBMemory class to control behavior.
        mock_memory = MagicMock(spec=LanceDBMemory)
        mock_memory.add.return_value = ["id1", "id2"]
        mock_memory.delete_by_metadata.return_value = True
        mock_memory._open_table.return_value = None  # Simulate missing table

        # Also mock CodeChunker to avoid real chunking
        mock_chunker = MagicMock(spec=CodeChunker)
        mock_chunker.chunk.return_value = {"chunk1": "code piece"}

        # Mock the read_file utility (likely from mle.utils.files)
        with patch('mle.cli.LanceDBMemory', return_value=mock_memory), \
             patch('mle.cli.CodeChunker', return_value=mock_chunker), \
             patch('mle.cli.read_file', return_value="dummy code"), \
             patch('mle.cli.list_files', return_value=[test_file, test_file2]), \
             patch('mle.cli.os.getcwd', return_value=tmpdir), \
             patch('mle.cli.os.path.isdir', side_effect=lambda p: p == tmpdir), \
             patch('mle.cli.console', MagicMock()):

            # Test --add
            result = runner.invoke(cli, ['memory', '--add', tmpdir])
            # The command should not crash. In buggy code, if _open_table is missing,
            # it will raise AttributeError. After fix, it should proceed.
            # We'll assert that the command exits with 0 (success) after fix.
            # Before fix, the test will fail due to AttributeError.
            assert result.exit_code == 0, f"Add failed: {result.output}"
            # Verify that add was called for each file
            assert mock_memory.add.call_count == 2

            # Reset mock for rm test
            mock_memory.reset_mock()
            # Test --rm
            result = runner.invoke(cli, ['memory', '--rm', test_file])
            assert result.exit_code == 0, f"Remove failed: {result.output}"
            mock_memory.delete_by_metadata.assert_called_once_with(
                key="file", value=test_file, table_name='mle_chat_' + os.path.basename(tmpdir)
            )

            # Reset mock for update test
            mock_memory.reset_mock()
            # Test --update
            result = runner.invoke(cli, ['memory', '--update', test_file2])
            assert result.exit_code == 0, f"Update failed: {result.output}"
            # Update should call delete then add
            assert mock_memory.delete_by_metadata.call_count == 1
            assert mock_memory.add.call_count == 1

def test_memory_cli_no_path():
    """Test that memory command with no path does nothing."""
    runner = CliRunner()
    result = runner.invoke(cli, ['memory'])
    assert result.exit_code == 0
    assert result.output == ''

def test_memory_cli_single_file():
    """Test memory command with a single file (not directory)."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "single.py")
        with open(test_file, "w") as f:
            f.write("x = 1")
        mock_memory = MagicMock(spec=LanceDBMemory)
        mock_memory.add.return_value = ["id"]
        mock_chunker = MagicMock(spec=CodeChunker)
        mock_chunker.chunk.return_value = {"chunk1": "code"}
        with patch('mle.cli.LanceDBMemory', return_value=mock_memory), \
             patch('mle.cli.CodeChunker', return_value=mock_chunker), \
             patch('mle.cli.read_file', return_value="dummy"), \
             patch('mle.cli.list_files', return_value=[test_file]), \
             patch('mle.cli.os.getcwd', return_value=tmpdir), \
             patch('mle.cli.os.path.isdir', return_value=False), \
             patch('mle.cli.console', MagicMock()):
            result = runner.invoke(cli, ['memory', '--add', test_file])
            assert result.exit_code == 0
            mock_memory.add.assert_called_once()
            # Check metadata includes file path
            call_kwargs = mock_memory.add.call_args[1]
            assert call_kwargs['metadata'] == [{'file': test_file, 'chunk_key': 'chunk1'}]

def test_memory_cli_table_name_generation():
    """Ensure table name is derived from current directory."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "dummy.py")
        with open(test_file, "w") as f:
            f.write("")
        mock_memory = MagicMock()
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = {"c": "code"}
        with patch('mle.cli.LanceDBMemory', return_value=mock_memory), \
             patch('mle.cli.CodeChunker', return_value=mock_chunker), \
             patch('mle.cli.read_file', return_value=""), \
             patch('mle.cli.list_files', return_value=[test_file]), \
             patch('mle.cli.os.getcwd', return_value=tmpdir), \
             patch('mle.cli.os.path.isdir', return_value=False), \
             patch('mle.cli.console', MagicMock()):
            runner.invoke(cli, ['memory', '--add', test_file])
            expected_table = 'mle_chat_' + os.path.basename(tmpdir)
            mock_memory.add.assert_called_once()
            call_kwargs = mock_memory.add.call_args[1]
            assert call_kwargs['table_name'] == expected_table