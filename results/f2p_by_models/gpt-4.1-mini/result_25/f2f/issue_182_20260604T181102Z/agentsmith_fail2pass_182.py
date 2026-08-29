import os
import subprocess

import pytest
from click.testing import CliRunner

import mle.cli as cli_module


@pytest.mark.timeout(60)
def test_cli_report_combines_pnpm_dev_and_mle_serve(monkeypatch):
    """
    Test that 'mle report' command with visualize=True runs both 'pnpm dev' and 'mle serve' logic.

    Fail2pass:
    - On buggy codebase, this test should fail (exit code != 0).
    - After fix, this test should pass (exit code == 0).

    This test uses CliRunner to invoke the CLI commands and patches subprocess.run to simulate
    pnpm and npm commands without actually running them.

    It also patches uvicorn.run to prevent real server start.
    """

    # Patch subprocess.run to simulate pnpm and npm commands success
    original_run = subprocess.run

    def fake_subprocess_run(args, **kwargs):
        # Simulate 'pnpm install' and 'pnpm dev' success
        if args[0] in ('pnpm', 'npm'):
            class CompletedProcess:
                def __init__(self):
                    self.returncode = 0
            return CompletedProcess()
        # For 'which' command in check_installed
        if args[0] == 'which':
            # Simulate that 'pnpm' is installed
            if args[1] == 'pnpm':
                class CompletedProcess:
                    def __init__(self):
                        self.returncode = 0
                        self.stdout = '/usr/bin/pnpm\n'
                return CompletedProcess()
            if args[1] == 'npm':
                class CompletedProcess:
                    def __init__(self):
                        self.returncode = 0
                        self.stdout = '/usr/bin/npm\n'
                return CompletedProcess()
        # For other commands, call original
        return original_run(args, **kwargs)

    # Patch uvicorn.run to prevent actual server start and just record call
    import uvicorn

    uvicorn_called = {}

    def fake_uvicorn_run(app, host, port, log_level=None):
        uvicorn_called['called'] = True
        uvicorn_called['host'] = host
        uvicorn_called['port'] = port
        uvicorn_called['log_level'] = log_level

    # Patch startup_web to just record call without running pnpm/npm
    startup_web_called = {}

    def fake_startup_web(host='0.0.0.0', port=3000):
        startup_web_called['called'] = True
        startup_web_called['host'] = host
        startup_web_called['port'] = port

    # Apply patches
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(uvicorn, "run", fake_uvicorn_run)
    monkeypatch.setattr(cli_module, "startup_web", fake_startup_web)

    runner = CliRunner()

    # Run 'mle report' with visualize=True (default)
    # This should trigger both serve and web commands internally
    result = runner.invoke(cli_module.cli, ['report', '--visualize'])

    # Assert the command exited without error
    assert result.exit_code == 0, f"CLI 'mle report --visualize' failed: {result.output}"

    # Assert that uvicorn.run was called (serve command)
    assert uvicorn_called.get('called', False), "uvicorn.run was not called by 'mle report --visualize'"

    # Assert that startup_web was called (web command)
    assert startup_web_called.get('called', False), "startup_web was not called by 'mle report --visualize'"


def test_cli_report_non_visualize_runs_report(monkeypatch):
    """
    Test that 'mle report' with visualize=False invokes workflow.report.

    We patch workflow.report to a dummy function to verify it is called.
    """

    import mle.workflow

    called = {}

    def fake_report(work_dir, repo, user, model):
        called['called'] = True
        called['work_dir'] = work_dir
        called['repo'] = repo
        called['user'] = user
        called['model'] = model
        return True

    monkeypatch.setattr(mle.workflow, 'report', fake_report)

    runner = CliRunner()

    # Provide valid repo and user, disable visualize
    result = runner.invoke(
        cli_module.cli,
        ['report', 'MLSysOps/MLE-agent', '--user', 'testuser', '--no-visualize'],
    )

    # Assert the command exited without error
    assert result.exit_code == 0, f"CLI 'mle report' failed: {result.output}"

    # Assert that workflow.report was called
    assert called.get('called', False), "'workflow.report' was not called by 'mle report --no-visualize'"


def test_cli_start_report_invokes_report(monkeypatch):
    """
    Test that 'mle start report' invokes the report command internally.
    """

    runner = CliRunner()

    called = {}

    def fake_report(ctx, repo=None, model=None, user=None, visualize=True):
        called['called'] = True
        called['repo'] = repo
        called['model'] = model
        called['user'] = user
        called['visualize'] = visualize
        return True

    monkeypatch.setattr(cli_module, 'report', fake_report)

    # Run 'mle start report'
    result = runner.invoke(cli_module.cli, ['start', 'report'])

    assert result.exit_code == 0, f"CLI 'mle start report' failed: {result.output}"
    assert called.get('called', False), "'report' command was not invoked by 'start report'"