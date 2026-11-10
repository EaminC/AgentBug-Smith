import pytest
from agentscope.service.execute_code.exec_shell import execute_shell_command, ServiceExecStatus


def test_execute_shell_command_blocks_insecure_commands():
    # Commands that should be blocked by the security fix
    insecure_commands = [
        "shutdown now",
        "kill -9 1234",
        "reboot",
        "pkill python",
        "useradd hacker",
        "userdel admin",
        "usermod -aG sudo user",
        "rm -rf /important/data",
    ]

    for cmd in insecure_commands:
        response = execute_shell_command(cmd)
        # The response status should be ERROR for insecure commands
        assert response.status == ServiceExecStatus.ERROR, f"Command '{cmd}' was not blocked as expected."
        # The response content should mention blocking for security reasons
        assert "blocked for security reasons" in response.content


def test_execute_shell_command_allows_safe_commands():
    # Commands that should be allowed (safe commands)
    safe_commands = [
        "echo hello",
        "ls -la",
        "pwd",
        "whoami",
        "date",
    ]

    for cmd in safe_commands:
        response = execute_shell_command(cmd)
        # The response status should NOT be ERROR for safe commands
        assert response.status != ServiceExecStatus.ERROR, f"Safe command '{cmd}' was blocked unexpectedly."
        # The content should contain the command output or be non-empty
        assert response.content is not None and response.content != ""


def test_insecure_commands_list_is_set_and_non_empty():
    # The insecure_commands list should exist and contain known commands
    assert hasattr(execute_shell_command, "insecure_commands")
    assert isinstance(execute_shell_command.insecure_commands, list)
    assert len(execute_shell_command.insecure_commands) > 0
    # Check some known insecure commands are in the list
    for cmd in ["shutdown", "kill", "rm -rf"]:
        assert any(cmd in icmd for icmd in execute_shell_command.insecure_commands)
