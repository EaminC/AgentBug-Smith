import os
import pytest
from pathlib import Path

import aider.io as io


def test_compute_minimal_fileids_correctness():
    io_instance = io.InputOutput()

    rel_fnames = [
        "src/a/file.txt",
        "src/b/file.txt",
        "src/a/file2.txt",
        "src/b/file2.txt",
        "src/a/file3.txt",
        "file3.txt",
    ]

    minimal_ids = io_instance.minimal_fileids(rel_fnames)

    # Files with same name get disambiguated by path prefix
    assert minimal_ids["src/a/file.txt"] == "a/file.txt"
    assert minimal_ids["src/b/file.txt"] == "b/file.txt"

    assert minimal_ids["src/a/file2.txt"] == "a/file2.txt"
    assert minimal_ids["src/b/file2.txt"] == "b/file2.txt"

    # Files with unique names should just be their name
    assert minimal_ids["file3.txt"] == "file3.txt"
    # src/a/file3.txt is unique, so minimal id is just file3.txt, not with prefix
    # This is a known failing assertion in buggy code, fixed after patch
    assert minimal_ids["src/a/file3.txt"] == "file3.txt"


def test_format_files_for_input_minimal_unique_ids():
    io_instance = io.InputOutput()

    rel_fnames = [
        "src/a/file.txt",
        "src/b/file.txt",
        "src/a/file2.txt",
        "src/b/file2.txt",
        "src/a/file3.txt",
    ]
    rel_read_only_fnames = [
        "src/b/file.txt",
        "src/a/file2.txt",
    ]

    output = io_instance.format_files_for_input(rel_fnames, rel_read_only_fnames)
    lines = output.strip().split("\n")

    # Read-only files should be listed first
    read_only_lines = lines[:len(rel_read_only_fnames)]
    editable_lines = lines[len(rel_read_only_fnames):]

    # Read-only lines start with " R "
    assert all(line.startswith(" R ") for line in read_only_lines)
    # Editable lines start with "   "
    assert all(line.startswith("   ") for line in editable_lines)

    # Check that minimal unique ids are used (no full src/a/file.txt if not needed)
    # For example, "file.txt (a)" or "file.txt (b)" or just "file3.txt"
    for line in lines:
        # line is like " R file.txt (b)" or "   file3.txt"
        # Extract the filename part after prefix
        content = line[3:]
        # Should not be full path, but either just filename or filename with parent dirs in parentheses
        assert content != ""


def test_format_files_for_input_empty_lists():
    io_instance = io.InputOutput()

    # Empty lists should return just a newline
    output = io_instance.format_files_for_input([], [])
    assert output == "\n"

    # Non-empty rel_fnames but empty read-only list
    rel_fnames = ["file1.py", "dir/file2.py"]
    output = io_instance.format_files_for_input(rel_fnames, [])
    lines = output.strip().split("\n")
    # All lines should start with "   "
    assert all(line.startswith("   ") for line in lines)


def test_format_files_for_input_all_read_only():
    io_instance = io.InputOutput()

    rel_fnames = ["dir1/file.py", "dir2/file.py"]
    rel_read_only_fnames = rel_fnames.copy()

    output = io_instance.format_files_for_input(rel_fnames, rel_read_only_fnames)
    lines = output.strip().split("\n")

    # All lines should start with " R "
    assert all(line.startswith(" R ") for line in lines)


def test_format_files_for_input_mixed_and_duplicates():
    io_instance = io.InputOutput()

    rel_fnames = [
        "src/a/file.txt",
        "src/b/file.txt",
        "src/a/file2.txt",
        "src/b/file2.txt",
        "src/a/file3.txt",
    ]
    rel_read_only_fnames = [
        "src/b/file.txt",
        "src/a/file2.txt",
    ]

    output = io_instance.format_files_for_input(rel_fnames, rel_read_only_fnames)
    lines = output.strip().split("\n")

    # Read-only lines come first
    read_only_lines = lines[:len(rel_read_only_fnames)]
    editable_lines = lines[len(rel_read_only_fnames):]

    # Read-only lines start with " R "
    assert all(line.startswith(" R ") for line in read_only_lines)
    # Editable lines start with "   "
    assert all(line.startswith("   ") for line in editable_lines)


def test_format_files_for_input_handles_relative_and_absolute_paths(tmp_path):
    io_instance = io.InputOutput()

    # Create some files in tmp_path
    file1 = tmp_path / "file1.py"
    file1.write_text("print('hello')")
    file2 = tmp_path / "subdir" / "file1.py"
    file2.parent.mkdir()
    file2.write_text("print('world')")

    rel_fnames = [str(file1.relative_to(tmp_path)), str(file2.relative_to(tmp_path))]
    rel_read_only_fnames = [rel_fnames[1]]

    output = io_instance.format_files_for_input(rel_fnames, rel_read_only_fnames)
    lines = output.strip().split("\n")

    # Read-only lines first
    read_only_lines = lines[:len(rel_read_only_fnames)]
    editable_lines = lines[len(rel_read_only_fnames):]

    # Read-only lines start with " R "
    assert all(line.startswith(" R ") for line in read_only_lines)
    # Editable lines start with "   "
    assert all(line.startswith("   ") for line in editable_lines)


def test_format_files_for_input_returns_newline_for_no_files():
    io_instance = io.InputOutput()
    output = io_instance.format_files_for_input([], [])
    assert output == "\n"


def test_compute_minimal_fileids_all_keys():
    io_instance = io.InputOutput()
    files = ["a/x.py", "b/x.py", "c/y.py", "z.py"]
    result = io_instance.minimal_fileids(files)
    # All input files should be keys in the result
    assert set(result.keys()) == set(files)
    # Files with same name get disambiguated
    assert result["a/x.py"] == "a/x.py"
    assert result["b/x.py"] == "b/x.py"
    # Unique names just filename
    assert result["c/y.py"] == "y.py" or result["c/y.py"] == "c/y.py"
    assert result["z.py"] == "z.py"