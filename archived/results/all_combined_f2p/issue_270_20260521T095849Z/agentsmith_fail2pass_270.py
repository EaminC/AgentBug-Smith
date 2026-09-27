import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

mock_git_module = MagicMock()
mock_git_module.Repo = MagicMock()
mock_git_module.NULL_TREE = "mock_null_tree"

# Wire in submodules that internal dependencies inspect
mock_git_cmd = MagicMock()
mock_git_cmd.Git = MagicMock()
sys.modules['git'] = mock_git_module
sys.modules['git.cmd'] = mock_git_cmd
sys.modules['git.exc'] = MagicMock()

# Suppress GitPython's execution check warnings
os.environ["GIT_PYTHON_REFRESH"] = "quiet"


@pytest.fixture
def temp_py_file():
    """Generates an isolated temporary Python file for memory parsing operations."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as f:
        f.write("print('hello world')\n")
        f.flush()
        yield f.name
    try:
        os.unlink(f.name)
    except Exception:
        pass


@pytest.fixture
def mock_memory_backend():
    """
    Isolates external framework subroutines (LanceDB instances, CodeChunkers)
    to verify execution patterns cleanly without needing active physical databases.
    """
    with patch("mle.cli.LanceDBMemory") as mock_lancedb, \
         patch("mle.cli.CodeChunker") as mock_chunker, \
         patch("mle.cli.Progress") as mock_progress, \
         patch("mle.cli.read_file", return_value="print('mocked code')"):
        
        mock_chunker_instance = MagicMock()
        mock_chunker_instance.chunk.return_value = {"chunk_0": "print('mocked code')"}
        mock_chunker.return_value = mock_chunker_instance
        
        yield {
            "memory": mock_lancedb.return_value,
            "chunker": mock_chunker_instance
        }


def test_memory_cli_command_registration():
    try:
        from mle.cli import cli
    except Exception as err:
        pytest.fail(f"CLI infrastructure failed to load safely during lazy import: {err}")

    # The buggy version completely lacks the definition or registration of the memory command hook
    if "memory" not in cli.commands:
        raise AssertionError("CRITICAL BUG: 'memory' command hook is not registered within the base mle.cli module.")
    
    assert cli.commands["memory"].name == "memory"


def test_memory_add_execution_routing(mock_memory_backend, temp_py_file):
    from mle.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "--add", temp_py_file])
    assert result.exit_code == 0, f"CLI execution failed: {result.output}"
    mock_memory_backend["memory"].add.assert_called_once()


def test_memory_rm_execution_routing(mock_memory_backend, temp_py_file):
    from mle.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "--rm", temp_py_file])
    assert result.exit_code == 0, f"CLI execution failed: {result.output}"
    
    # Assert that delete subroutines were fired with metadata configurations matching the file path
    mock_memory_backend["memory"].delete_by_metadata.assert_called_once()


def test_memory_update_execution_routing(mock_memory_backend, temp_py_file):
    from mle.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "--update", temp_py_file])
    assert result.exit_code == 0, f"CLI execution failed: {result.output}"
    
    # Assert that update performs both CRUD deletion cycles and re-addition cycles sequentially
    mock_memory_backend["memory"].delete_by_metadata.assert_called_once()
    mock_memory_backend["memory"].add.assert_called_once()


def test_memory_no_options_exits_gracefully(mock_memory_backend):
    from mle.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ["memory"])
    assert result.exit_code == 0
    
    # Ensure no processing paths or database loops were executed
    mock_memory_backend["memory"].add.assert_not_called()
    mock_memory_backend["memory"].delete_by_metadata.assert_not_called()