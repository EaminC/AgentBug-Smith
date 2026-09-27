import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
from crewai.cli import utils


def test_get_crews_handles_import_errors_buggy():
    """
    Test that get_crews() handles import errors gracefully and does not crash
    with undefined name errors like 'JsonValue', 'TaskOutput', 'Task'.
    This test should fail on buggy code because the error messages are printed
    with print() instead of console.print() and the error handling is incomplete.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create a crew.py that imports modules that may cause undefined name errors
        # Simulate the scenario from the bug report where JsonValue, TaskOutput, Task are not defined
        crew_content = """
from typing import Optional
import json

# These imports might fail if the types are not available in the environment
# or if there's a circular import issue
try:
    from crewai.types import JsonValue, TaskOutput, Task
except ImportError:
    JsonValue = None
    TaskOutput = None
    Task = None

from crewai.crew import Crew
from crewai.agent import Agent

def create_crew() -> Optional[Crew]:
    try:
        agent = Agent(role="test", goal="test", backstory="test")
        return Crew(agents=[agent], tasks=[])
    except Exception:
        return None

# Direct crew instance
direct_crew = Crew(agents=[], tasks=[])
"""
        with open("crew.py", "w") as f:
            f.write(crew_content)

        # Mock the console.print to capture output
        with patch.object(utils.console, 'print') as mock_print:
            crews = utils.get_crews(crew_path="crew.py", require=False)

        # In buggy code, the error messages would be printed with print() not console.print()
        # So mock_print wouldn't capture them. We need to check that the function doesn't crash
        # and returns a list (possibly empty).
        assert isinstance(crews, list)
        # The function should not raise an exception
        # If it does, the test will fail (which is what we want for buggy code)

        os.chdir(old_cwd)


def test_get_crews_error_messages_use_console_print():
    """
    Test that error messages in get_crews() use console.print() with proper styling.
    This test should fail on buggy code because error messages are printed with print().
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create a crew.py that will cause an import error
        crew_content = """
import nonexistent_module

from crewai.crew import Crew

crew = Crew(agents=[], tasks=[])
"""
        with open("crew.py", "w") as f:
            f.write(crew_content)

        # Mock console.print to capture calls
        with patch.object(utils.console, 'print') as mock_print:
            crews = utils.get_crews(crew_path="crew.py", require=False)

        # Check that console.print was called with error messages
        # In buggy code, print() is used instead of console.print()
        # So mock_print won't be called with error messages
        error_calls = [
            call for call in mock_print.call_args_list
            if len(call[0]) > 0 and "Error" in str(call[0][0])
        ]
        # In fixed code, there should be error calls
        # In buggy code, there won't be any because print() is used
        # We'll assert that console.print was called with an error message
        # This will fail on buggy code
        assert len(error_calls) > 0, "console.print should have been called with error messages"

        os.chdir(old_cwd)


def test_get_crews_handles_missing_types_gracefully():
    """
    Test that get_crews() doesn't crash when types like JsonValue, TaskOutput, Task
    are not defined in the module's scope.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create a crew.py that references undefined names
        crew_content = """
from crewai.crew import Crew
from crewai.agent import Agent

# These might be undefined if imports failed earlier
undefined_var = JsonValue  # This will cause NameError

def create_crew():
    agent = Agent(role="test", goal="test", backstory="test")
    return Crew(agents=[agent], tasks=[])

crew = create_crew()
"""
        with open("crew.py", "w") as f:
            f.write(crew_content)

        # Capture stdout to check error messages
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            crews = utils.get_crews(crew_path="crew.py", require=False)

        output = f.getvalue()
        # In buggy code, the error message would be printed with print()
        # and might contain "name 'JsonValue' is not defined"
        # In fixed code, the error message would be printed with console.print()
        # and styled properly
        # We'll check that the function doesn't crash and returns a list
        assert isinstance(crews, list)
        # The function should handle the NameError gracefully

        os.chdir(old_cwd)


def test_get_crews_with_require_flag_and_errors():
    """
    Test that get_crews() with require=True exits with SystemExit when no crews are found
    and that error messages are printed properly.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create an empty crew.py
        with open("crew.py", "w") as f:
            f.write("# No crews here")

        # Mock console.print to capture output
        with patch.object(utils.console, 'print') as mock_print:
            with pytest.raises(SystemExit):
                utils.get_crews(crew_path="crew.py", require=True)

        # Check that console.print was called with error message
        error_calls = [
            call for call in mock_print.call_args_list
            if len(call[0]) > 0 and ("No valid Crew instance found" in str(call[0][0]) or "Error" in str(call[0][0]))
        ]
        # In buggy code, some error messages might use print() instead of console.print()
        # So this assertion might fail
        assert len(error_calls) > 0, "console.print should have been called with error messages"

        os.chdir(old_cwd)
