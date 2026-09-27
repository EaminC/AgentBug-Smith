import sys
import io

from gpt_engineer.core.chat_to_files import parse_diffs

multi_diff = """
```
--- a/file1.txt
+++ a/file1.txt
@@ -1,3 +1,3 @@
-old line
+new line
```
```
--- a/file1.txt
+++ a/file1.txt
@@ -2,3 +2,3 @@
-another old line
+another new line
```
"""


def test_multi_diff_keeps_first():
    """
    When multiple diffs for the same file appear in the chat,
    the buggy version overwrites with the last diff. The fix
    keeps only the first diff per file.
    """
    # On buggy code, the second diff overwrites the first.
    # On fixed code, only the first diff is kept.
    diffs = parse_diffs(multi_diff)

    # We expect exactly one file key
    assert "a/file1.txt" in diffs

    # The diff should be the first block only
    first_block_lines = [
        "--- a/file1.txt",
        "+++ a/file1.txt",
        "@@ -1,3 +1,3 @@",
        "-old line",
        "+new line",
    ]
    expected_diff = "\n".join(first_block_lines)
    actual_diff = diffs["a/file1.txt"].diff_to_string().strip()
    assert actual_diff == expected_diff


def test_multi_diff_print_warning():
    """
    On the fixed version, a warning is printed when multiple diffs
    for the same file are found. The buggy version does not print it.
    """
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        parse_diffs(multi_diff)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    # The buggy code does not print this message; the fixed code does.
    assert "Multiple diffs found for a/file1.txt" in output
