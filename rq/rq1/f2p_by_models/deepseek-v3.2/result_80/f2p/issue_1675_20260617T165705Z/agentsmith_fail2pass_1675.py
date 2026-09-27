import pytest
from pathlib import Path
from aider.io import InputOutput


def test_format_files_for_input_no_read_only():
    """Test that format_files_for_input works with no read-only files."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/astra.py",
    ]
    rel_read_only_fnames = []

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    # Should contain both files
    assert "astra.py" in result
    assert "db.py" in result

    # All should be editable (have "   " prefix for 3 spaces)
    lines = result.rstrip('\n').split('\n')
    assert all(line.startswith("   ") for line in lines), f"All files should be editable with '   ' prefix. Got: {repr(result)}"


def test_format_files_for_input_with_read_only():
    """Test that format_files_for_input properly displays both editable and read-only files."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/astra.py",
    ]
    rel_read_only_fnames = [
        "colbert_live/db/astra.py",
    ]

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    # Should contain both files
    assert "astra.py" in result
    assert "db.py" in result

    # Read-only file should have " R " prefix
    lines = result.rstrip('\n').split('\n')
    assert any(line.startswith(" R ") for line in lines), f"Should have read-only marker. Got: {repr(result)}"


def test_compute_minimal_fileids_same_name():
    """Test that compute_minimal_fileids properly disambiguates files with same name."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/db.py",
    ]

    result = io.compute_minimal_fileids(rel_fnames)

    assert isinstance(result, dict)
    assert len(result) == 2
    # Both should have different minimal ids to disambiguate
    assert result["example/cmdline/db.py"] != result["colbert_live/db/db.py"]


def test_compute_minimal_fileids_different_names():
    """Test that compute_minimal_fileids works with files of different names."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/astra.py",
    ]

    result = io.compute_minimal_fileids(rel_fnames)

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "example/cmdline/db.py" in result
    assert "colbert_live/db/astra.py" in result


def test_format_files_for_input_with_disambiguating_path():
    """Test that files with same name get disambiguating paths in output."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/db.py",
    ]
    rel_read_only_fnames = []

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    # Both files should be present
    assert "db.py" in result
    # Should have path disambiguation in parentheses
    assert "(" in result and ")" in result


def test_format_files_for_input_read_only_indicator():
    """Test that read-only files are marked with R indicator."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/astra.py",
    ]
    rel_read_only_fnames = [
        "colbert_live/db/astra.py",
    ]

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    lines = result.rstrip('\n').split('\n')

    # Should have at least one read-only marker
    has_read_only_marker = any(line.startswith(" R ") for line in lines)
    assert has_read_only_marker, f"Should have at least one read-only file marked with ' R '. Got: {repr(result)}"


def test_format_files_for_input_editable_indicator():
    """Test that editable files are marked with spaces indicator."""
    io = InputOutput()

    rel_fnames = [
        "example/cmdline/db.py",
        "colbert_live/db/astra.py",
    ]
    rel_read_only_fnames = [
        "colbert_live/db/astra.py",
    ]

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    lines = result.rstrip('\n').split('\n')

    # Should have at least one editable marker
    has_editable_marker = any(line.startswith("   ") for line in lines)
    assert has_editable_marker, f"Should have at least one editable file marked with '   '. Got: {repr(result)}"


def test_compute_minimal_fileids_single_file():
    """Test compute_minimal_fileids with a single file."""
    io = InputOutput()

    rel_fnames = [
        "colbert_live/db/astra.py",
    ]

    result = io.compute_minimal_fileids(rel_fnames)

    assert isinstance(result, dict)
    assert len(result) == 1
    assert "colbert_live/db/astra.py" in result


def test_compute_minimal_fileids_nested_same_name():
    """Test compute_minimal_fileids with deeply nested files of same name."""
    io = InputOutput()

    rel_fnames = [
        "a/b/c/test.py",
        "x/y/z/test.py",
    ]

    result = io.compute_minimal_fileids(rel_fnames)

    assert isinstance(result, dict)
    assert len(result) == 2
    # Both should have different minimal ids to disambiguate
    assert result["a/b/c/test.py"] != result["x/y/z/test.py"]


def test_format_files_for_input_issue_1675_scenario():
    """Test the exact scenario from issue 1675: astra.py and db.py confusion."""
    io = InputOutput()

    # The issue: aider says astra.py is in context but LLM acts like it isn't
    rel_fnames = [
        "colbert_live/db/astra.py",
        "example/cmdline/db.py",
    ]
    rel_read_only_fnames = []

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    # Both files should be clearly visible
    assert "astra.py" in result
    assert "db.py" in result

    # Should have proper formatting with indicators
    lines = result.rstrip('\n').split('\n')
    assert len(lines) >= 2, "Should have at least 2 lines for 2 files"

    # All should be editable (no read-only marker)
    assert not any(line.startswith(" R ") for line in lines), "No files should be read-only"

    # All should have editable marker
    assert all(line.startswith("   ") for line in lines), f"All files should be editable. Got: {repr(result)}"


def test_format_files_for_input_returns_string_with_newline():
    """Test that format_files_for_input returns a string ending with newline."""
    io = InputOutput()

    rel_fnames = ["test.py"]
    rel_read_only_fnames = []

    result = io.format_files_for_input(rel_fnames, rel_read_only_fnames)

    assert isinstance(result, str)
    assert result.endswith('\n'), "Result should end with newline"


def test_compute_minimal_fileids_returns_dict():
    """Test that compute_minimal_fileids returns a dictionary."""
    io = InputOutput()

    rel_fnames = ["test.py"]

    result = io.compute_minimal_fileids(rel_fnames)

    assert isinstance(result, dict)
    assert "test.py" in result
