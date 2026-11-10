import os
import tempfile
import shutil
import pytest
from click.testing import CliRunner
from mle.cli import memory
from mle.utils.memory import LanceDBMemory


def create_temp_py_file(dir_path, filename, content):
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


@pytest.fixture
def temp_project_dir():
    # Create a temporary directory to simulate a project directory
    temp_dir = tempfile.mkdtemp(prefix="mle_test_project_")
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_memory_add_rm_update_cycle(temp_project_dir):
    runner = CliRunner()

    # Create two python files in the temp directory
    file1 = create_temp_py_file(temp_project_dir, "file1.py", "print('hello world')\n")
    file2 = create_temp_py_file(temp_project_dir, "file2.py", "def foo():\n    return 42\n")

    # Change working directory to temp_project_dir for the CLI command
    old_cwd = os.getcwd()
    os.chdir(temp_project_dir)

    try:
        # 1) Add files to memory
        result_add = runner.invoke(memory, ["--add", file1])
        assert result_add.exit_code == 0, f"Add command failed: {result_add.output}"

        result_add_dir = runner.invoke(memory, ["--add", temp_project_dir])
        assert result_add_dir.exit_code == 0, f"Add dir command failed: {result_add_dir.output}"

        # Instantiate memory to check contents
        mem = LanceDBMemory(temp_project_dir)
        table_name = "mle_chat_" + os.path.basename(temp_project_dir)

        # After add, the memory should contain keys related to the files
        keys = mem.list_all_keys(table_name)
        assert len(keys) > 0, "Memory should have keys after adding files"

        # 2) Remove one file from memory
        result_rm = runner.invoke(memory, ["--rm", file1])
        assert result_rm.exit_code == 0, f"Remove command failed: {result_rm.output}"

        # After removal, no chunks with file1 should remain
        records = mem.get_by_metadata("file", file1, table_name)
        assert records == [], "Memory should have no chunks for removed file"

        # 3) Update the other file (should remove old chunks and add new ones)
        # Modify file2 content
        with open(file2, "w", encoding="utf-8") as f:
            f.write("def foo():\n    return 100\n")

        result_update = runner.invoke(memory, ["--update", file2])
        assert result_update.exit_code == 0, f"Update command failed: {result_update.output}"

        # After update, memory should have chunks for file2
        records_after_update = mem.get_by_metadata("file", file2, table_name)
        assert len(records_after_update) > 0, "Memory should have chunks for updated file"

    finally:
        os.chdir(old_cwd)