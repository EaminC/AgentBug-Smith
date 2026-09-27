import io
import json
import textwrap
from pathlib import Path
from unittest import mock

import pytest

import scripts.benchmark as benchmark


@pytest.fixture
def tmp_benchmark_dir(tmp_path):
    # Setup a fake benchmark folder structure with memory/review file and RESULTS.md
    bench_dir = tmp_path / "test_benchmark"
    bench_dir.mkdir()
    memory_dir = bench_dir / "memory"
    memory_dir.mkdir()
    review_data = {
        "ran": True,
        "works": True,
        "perfect": True,
        "comments": "All good",
    }
    (memory_dir / "review").write_text(json.dumps(review_data))

    results_md = tmp_path / "RESULTS.md"
    # Pre-fill RESULTS.md with a header and a dummy old section to test insertion
    results_md.write_text(
        textwrap.dedent(
            """\
            # Results

            ## 2023-01-01

            Old content
            """
        )
    )

    return tmp_path, bench_dir, results_md


def test_generate_report_creates_correct_table_and_inserts_section(tmp_benchmark_dir):
    tmp_path, bench_dir, results_md = tmp_benchmark_dir

    benchmarks = [(bench_dir, None, None)]

    # Patch input to simulate user saying 'y' to append report
    with mock.patch("builtins.input", side_effect=["y"]):
        # Patch datetime.now().strftime to fixed date for predictable output
        with mock.patch("scripts.benchmark.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-06-01"
            benchmark.generate_report(benchmarks, tmp_path)

    # Check that RESULTS.md now contains the inserted markdown section at level 2 header
    content = results_md.read_text()
    # The inserted section header
    assert "## 2024-06-01" in content
    # The table header line with correct alignment (tabulate pipe table)
    assert "| Benchmark      | Ran   | Works   | Perfect   | Notes    |" in content
    # The row with our benchmark name and emojis
    assert "| test_benchmark | ✅     | ✅       | ✅         | All good |" in content
    # The old section remains after the new inserted section
    assert "## 2023-01-01" in content
    assert "Old content" in content


def test_to_emoji_returns_correct_emoji():
    assert benchmark.to_emoji(True) == "\u2705"
    assert benchmark.to_emoji(False) == "\u274C"
    assert benchmark.to_emoji(None) == "\u274C"


def test_insert_markdown_section_inserts_at_correct_place(tmp_path):
    file_path = tmp_path / "file.md"
    # File with two level 2 headers
    file_path.write_text("# Title\n\n## Header1\nContent1\n\n## Header2\nContent2\n")

    benchmark.insert_markdown_section(file_path, "New Section", "Section content", 2)

    content = file_path.read_text()
    # The new section should be inserted before the first level 2 header
    expected_start = "## New Section\n\nSection content\n\n"
    assert content.startswith("# Title\n\n" + expected_start)
    # The rest of the content remains
    assert "## Header1" in content
    assert "Content1" in content
    assert "## Header2" in content
    assert "Content2" in content


def test_insert_markdown_section_no_level_found_prints_and_does_not_write(tmp_path, capsys):
    file_path = tmp_path / "file.md"
    # File with only level 1 headers (no level 2)
    file_path.write_text("# Title\n\n# Another Title\n")

    original_content = file_path.read_text()

    benchmark.insert_markdown_section(file_path, "New Section", "Section content", 2)

    captured = capsys.readouterr()
    assert "Markdown file was of unexpected format" in captured.out

    # File content should be unchanged
    assert file_path.read_text() == original_content


def test_ask_yes_no_accepts_y_and_n(monkeypatch):
    inputs = iter(["maybe", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert benchmark.ask_yes_no("Question?") is True

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert benchmark.ask_yes_no("Question?") is False

    inputs = iter(["", "no", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert benchmark.ask_yes_no("Question?") is False


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, "\u2705"),
        (False, "\u274C"),
        (None, "\u274C"),
    ],
)
def test_to_emoji_parametrized(value, expected):
    assert benchmark.to_emoji(value) == expected
