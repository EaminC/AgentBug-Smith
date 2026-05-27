import pytest
from agentscope.service.execute_code.exec_shell import execute_shell_command, ServiceExecStatus


def test_execute_shell_command_blocks_insecure_commands():
    # These commands should be blocked by the security check
    insecure_commands = [
        "shutdown now",
        "kill -9 1234",
        "reboot",
        "pkill python",
        "useradd hacker",
        "userdel guest",
        "usermod -aG sudo user",
        "rm -rf /",
        "rm -rf /tmp/test",
    ]

    for cmd in insecure_commands:
        response = execute_shell_command(cmd)
        # The response status should be ERROR for blocked commands
        assert response.status == ServiceExecStatus.ERROR, f"Command '{cmd}' was not blocked"
        # The content should mention blocking for security reasons
        assert "blocked for security reasons" in response.content


def test_execute_shell_command_allows_safe_commands():
    # These commands should be allowed (assuming they are safe)
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
        assert response.status != ServiceExecStatus.ERROR, f"Safe command '{cmd}' was blocked"
        # The content should contain the command output or be non-empty
        assert response.content is not None and response.content != ""


@pytest.mark.parametrize("cmd", [
    "rm -rf /tmp/somefolder",
    "rm -rf /tmp/somefolder && echo done",
    "rm -rf /tmp/somefolder; ls",
])
def test_execute_shell_command_blocks_rm_rf_variants(cmd):
    # Variants containing "rm -rf" should be blocked
    response = execute_shell_command(cmd)
    assert response.status == ServiceExecStatus.ERROR
    assert "blocked for security reasons" in response.content


def test_execute_shell_command_warning_logged(monkeypatch):
    logs = []

    def fake_warning(msg):
        logs.append(msg)

    # Patch logger.warning to capture warnings
    import agentscope.service.execute_code.exec_shell as exec_shell
    monkeypatch.setattr(exec_shell.logger, "warning", fake_warning)

    cmd = "shutdown now"
    response = execute_shell_command(cmd)

    assert response.status == ServiceExecStatus.ERROR
    assert any("blocked for security reasons" in log for log in logs)


def test_insecure_commands_list_contains_expected_entries():
    # The insecure_commands list should contain expected command substrings
    expected_substrings = [
        "shutdown",
        "kill",
        "reboot",
        "pkill",
        "useradd",
        "userdel",
        "usermod",
        "rm -rf",
    ]
    for substr in expected_substrings:
        assert any(substr in cmd for cmd in execute_shell_command.insecure_commands), (
            f"Expected insecure command substring '{substr}' not found in insecure_commands list"
        )
