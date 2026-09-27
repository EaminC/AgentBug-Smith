import pytest
from agentscope.service.execute_code.exec_shell import execute_shell_command
from agentscope.service.service_status import ServiceExecStatus


def test_insecure_command_blocked_by_security_check(monkeypatch):
    """Test that insecure commands are blocked before execution.
    
    Verifies the security fix for issue #411 where arbitrary code execution
    was possible. After the fix, commands containing insecure keywords like
    'shutdown' should be blocked and return an error without calling
    subprocess.run.
    """
    # Track whether subprocess.run was invoked
    subprocess_called = {"invoked": False}
    
    class MockCompletedProcess:
        returncode = 0
        stdout = "executed"
        stderr = ""
    
    def mock_subprocess_run(*args, **kwargs):
        subprocess_called["invoked"] = True
        return MockCompletedProcess()
    
    # Patch subprocess.run to prevent actual command execution
    monkeypatch.setattr(
        "agentscope.service.execute_code.exec_shell.subprocess.run",
        mock_subprocess_run,
    )
    
    # Attempt to execute a command that should be blocked (shutdown is in the default insecure list)
    command = "shutdown now"
    response = execute_shell_command(command)
    
    # In the fixed version, the command should be blocked before subprocess.run
    assert response.status == ServiceExecStatus.ERROR, (
        f"Expected ERROR status for insecure command, got {response.status}"
    )
    assert "blocked for security reasons" in response.content, (
        f"Expected security block message, got: {response.content}"
    )
    assert command in response.content, (
        f"Expected command name in error message, got: {response.content}"
    )
    assert subprocess_called["invoked"] is False, (
        "subprocess.run should not be called for insecure commands - "
        "security check failed to block execution"
    )
