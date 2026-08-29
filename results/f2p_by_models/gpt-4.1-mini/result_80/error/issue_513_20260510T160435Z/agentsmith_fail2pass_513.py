import pytest
import tempfile
import os
import sys
import subprocess
import re

from src.agentscope.web.workstation.workflow_dag import ASDiGraph


def test_workflow_dag_script_contains_utf8_encoding_declaration():
    """
    This test verifies that the generated script from ASDiGraph includes the UTF-8
    encoding declaration line. Without this line, scripts containing Chinese characters
    cause a SyntaxError in Python due to missing encoding declaration.

    The test will fail on the buggy codebase (missing encoding declaration),
    and pass after the fix (encoding declaration added).
    """
    # Create a dummy node with Chinese characters in the script body
    graph = ASDiGraph()

    # Add a node with a Chinese character in its script body
    node_id = "node1"
    # The node data must contain 'script' key with Chinese characters in it
    chinese_content = "print('你好，世界')"  # "Hello, World" in Chinese
    graph.add_node(node_id, script=chinese_content)

    # Generate the script from the graph
    script = graph.generate_script()

    # Check that the script contains the UTF-8 encoding declaration line
    # The fix adds: "# -*- coding: utf-8 -*-\n" at the top
    encoding_decl_pattern = r"^#\s*-\*-\s*coding:\s*utf-8\s*-\*-\s*$"

    # We check the first line of the script for the encoding declaration
    first_line = script.splitlines()[0]

    assert re.match(encoding_decl_pattern, first_line), (
        "The generated script does not contain the UTF-8 encoding declaration line. "
        "This causes SyntaxError when the script contains non-ASCII characters like Chinese."
    )

    # Additionally, check that the Chinese characters are present in the script
    assert chinese_content in script, "The Chinese content is missing in the generated script."


def test_generated_script_executes_without_syntax_error():
    """
    This test attempts to execute the generated script containing Chinese characters.
    Without the UTF-8 encoding declaration, Python raises a SyntaxError.
    After the fix, the script should run without syntax errors.
    """
    graph = ASDiGraph()

    node_id = "node1"
    chinese_content = "print('你好，世界')"  # Chinese greeting

    graph.add_node(node_id, script=chinese_content)

    script = graph.generate_script()

    # Write the script to a temporary file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp_file:
        tmp_file.write(script)
        tmp_path = tmp_file.name

    try:
        # Run the script with python subprocess
        # Capture stderr to check for SyntaxError
        proc = subprocess.run(
            [sys.executable, tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            timeout=5,
        )

        # The script should run successfully (returncode 0)
        # If the encoding declaration is missing, a SyntaxError occurs and returncode != 0
        assert proc.returncode == 0, (
            f"Script execution failed with return code {proc.returncode}.\n"
            f"stderr: {proc.stderr}"
        )

        # The output should contain the Chinese greeting printed
        assert "你好，世界" in proc.stdout, "The script did not print the expected Chinese output."

    finally:
        # Clean up the temporary file
        os.unlink(tmp_path)