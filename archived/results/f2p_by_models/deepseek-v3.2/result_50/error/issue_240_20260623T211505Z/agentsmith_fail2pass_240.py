import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import sys

import pytest

# Import what's actually available from scripts.benchmark
# Based on the errors, we need to check what functions exist
from scripts.benchmark import (
    main,
    to_emoji,
    insert_markdown_section,
    ask_yes_no,
)


def test_to_emoji():
    """Test to_emoji function."""
    assert to_emoji(True) == "✅"
    assert to_emoji(False) == "❌"


def test_ask_yes_no():
    """Test ask_yes_no function."""
    with patch("builtins.input", return_value="y"):
        assert ask_yes_no("Test?") is True
    with patch("builtins.input", return_value="n"):
        assert ask_yes_no("Test?") is False
    with patch("builtins.input", side_effect=["invalid", "y"]):
        with patch("builtins.print") as mock_print:
            assert ask_yes_no("Test?") is True
            mock_print.assert_called_with("Please enter either 'y' or 'n'.")


def test_insert_markdown_section():
    """Test insert_markdown_section function."""
    content = "# Title\n\n## Section 1\n\nText\n"
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(content)
        f.flush()
        insert_markdown_section(f.name, "New Section", "New text", 2)
        with open(f.name) as f2:
            result = f2.read()
    expected = "# Title\n\n## New Section\n\nNew text\n\n## Section 1\n\nText\n"
    assert result == expected


def test_main_with_n_benchmarks():
    """Test main with n_benchmarks argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        memory = bench / "memory"
        memory.mkdir()
        (memory / "review").write_text(
            json.dumps({"ran": True, "works": True, "perfect": True, "comments": ""})
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("builtins.input", return_value="n"):
                # Call main without parameters since it doesn't accept them
                # We'll need to mock sys.argv to simulate command line arguments
                with patch("sys.argv", ["benchmark", "--n-benchmarks", "1"]):
                    main()


def test_main_with_path_argument():
    """Test main with path argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        memory = bench / "memory"
        memory.mkdir()
        (memory / "review").write_text(
            json.dumps({"ran": True, "works": True, "perfect": True, "comments": ""})
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("builtins.input", return_value="n"):
                # Mock sys.argv to simulate path argument
                with patch("sys.argv", ["benchmark", "--path", str(benchmark_path)]):
                    main()


def test_main_with_run_all():
    """Test main with run_all=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        memory = bench / "memory"
        memory.mkdir()
        (memory / "review").write_text(
            json.dumps({"ran": True, "works": True, "perfect": True, "comments": ""})
        )
        with patch("subprocess.run") as mock_run:
            mock_run.returnvalue.returncode = 0
            with patch("builtins.input", return_value="n"):
                # Mock sys.argv to simulate run-all flag
                with patch("sys.argv", ["benchmark", "--path", str(benchmark_path), "--run-all"]):
                    main()


def test_main_without_review_files():
    """Test main when review files are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        # No memory folder
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("builtins.input", return_value="n"):
                # Mock sys.argv
                with patch("sys.argv", ["benchmark", "--path", str(benchmark_path), "--n-benchmarks", "1"]):
                    main()


def test_main_with_existing_results_md():
    """Test main when RESULTS.md exists and user chooses to append."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        results_md = benchmark_path / "RESULTS.md"
        results_md.write_text("# Results\n\n## 2024-01-01\n\nOld table\n")
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        memory = bench / "memory"
        memory.mkdir()
        (memory / "review").write_text(
            json.dumps({"ran": True, "works": True, "perfect": True, "comments": ""})
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("builtins.input", return_value="y"):
                with patch("scripts.benchmark.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = "2024-01-02"
                    # Mock sys.argv
                    with patch("sys.argv", ["benchmark", "--path", str(benchmark_path), "--n-benchmarks", "1"]):
                        main()


def test_main_with_failed_subprocess():
    """Test main when subprocess fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        bench = benchmark_path / "bench"
        bench.mkdir()
        (bench / "prompt").write_text("prompt")
        memory = bench / "memory"
        memory.mkdir()
        (memory / "review").write_text(
            json.dumps({"ran": False, "works": False, "perfect": False, "comments": "failed"})
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            with patch("builtins.input", return_value="n"):
                # Mock sys.argv
                with patch("sys.argv", ["benchmark", "--path", str(benchmark_path)]):
                    main()


def test_main_with_multiple_benchmarks():
    """Test main with multiple benchmarks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        benchmark_path = Path(tmpdir) / "benchmark"
        benchmark_path.mkdir()
        for i in range(3):
            bench = benchmark_path / f"bench{i}"
            bench.mkdir()
            (bench / "prompt").write_text("prompt")
            memory = bench / "memory"
            memory.mkdir()
            (memory / "review").write_text(
                json.dumps({"ran": True, "works": True, "perfect": True, "comments": f"bench{i}"})
            )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("builtins.input", return_value="n"):
                # Mock sys.argv
                with patch("sys.argv", ["benchmark", "--path", str(benchmark_path), "--n-benchmarks", "2"]):
                    main()


def test_main_default_path():
    """Test main with default path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            benchmark_path = Path("benchmark")
            benchmark_path.mkdir()
            bench = benchmark_path / "bench"
            bench.mkdir()
            (bench / "prompt").write_text("prompt")
            memory = bench / "memory"
            memory.mkdir()
            (memory / "review").write_text(
                json.dumps({"ran": True, "works": True, "perfect": True, "comments": ""})
            )
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                with patch("builtins.input", return_value="n"):
                    # Call main without arguments - should use default path
                    with patch("sys.argv", ["benchmark"]):
                        main()
        finally:
            os.chdir(original_cwd)


# Remove the test_generate_report function since generate_report doesn't exist
# Remove the test_main_with_n_benchmarks parameterized version since we fixed it above