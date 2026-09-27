import sys
import os
import subprocess

# Add the src directory to the path so we can import agentscope
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentscope.service import execute_shell_command
from agentscope.service.service_response import ServiceResponse
from agentscope.service.service_status import ServiceExecStatus


def test_execute_shell_command_security_blocked() -> None:
    """Test that insecure commands are blocked after the fix."""
    # This test should fail on buggy code (no blocking) and pass on fixed code (blocking).
    # The buggy code will execute the command; the fixed code will return an error.
    # We test a command that contains a blocked substring.
    # The patch adds a list `insecure_commands` that includes "rm -rf".
    # We'll use a command that includes "rm -rf" as a substring.
    command = "rm -rf /tmp/test"
    response = execute_shell_command(command)

    # On buggy code, the command will be executed and likely succeed (return 0).
    # On fixed code, the command will be blocked and return ServiceExecStatus.ERROR.
    # We assert that the response status is ERROR (i.e., the fix is applied).
    assert response.status == ServiceExecStatus.ERROR
    assert "blocked for security reasons" in response.content


def test_execute_shell_command_allowed() -> None:
    """Test that a safe command still works after the fix."""
    # A simple echo command should be allowed.
    # On buggy code, it will succeed.
    # On fixed code, it should also succeed (if not in insecure_commands).
    command = "echo hello"
    response = execute_shell_command(command)
    # Both buggy and fixed code should succeed for this command.
    assert response.status == ServiceExecStatus.SUCCESS
    assert "hello" in response.content


def test_execute_shell_command_insecure_list() -> None:
    """Test that the insecure_commands list is present and contains expected items."""
    # The patch adds an attribute `insecure_commands` to the function.
    # This test will fail on buggy code (attribute missing) and pass on fixed code.
    insecure_commands = execute_shell_command.insecure_commands
    assert isinstance(insecure_commands, list)
    # Check for some expected blocked commands from the patch.
    assert "rm -rf" in insecure_commands
    assert "shutdown" in insecure_commands
    assert "kill" in insecure_commands


def test_execute_shell_command_partial_match() -> None:
    """Test that a command containing an insecure substring is blocked."""
    # The patch checks if any insecure command is a substring of the given command.
    # So "sudo shutdown now" should be blocked because it contains "shutdown".
    command = "sudo shutdown now"
    response = execute_shell_command(command)
    # On buggy code, this will execute (may fail due to sudo, but status might be ERROR from subprocess).
    # We need to differentiate: buggy code will try to run the command and may return SUCCESS or ERROR from subprocess.
    # Fixed code will return ServiceExecStatus.ERROR with a blocking message.
    # We'll assert the blocking message is present.
    assert response.status == ServiceExecStatus.ERROR
    assert "blocked for security reasons" in response.content


def test_execute_shell_command_open_calculator() -> None:
    """Test the specific example from the issue: open -a calculator."""
    # The issue mentions that "open -a calculator" opens the calculator.
    # The patch does NOT include "open" in the insecure_commands list.
    # Therefore, on fixed code, this command will still execute.
    # However, the issue is about arbitrary code execution; the fix only blocks a specific list.
    # So this test is not a good fail2pass candidate because it will pass on both buggy and fixed code.
    # Instead, we should test a command that is in the insecure list.
    # But we can still test that the function works for this command.
    # We'll skip this test because it doesn't differentiate buggy vs fixed.
    pass


if __name__ == "__main__":
    # Simple test runner for debugging.
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
