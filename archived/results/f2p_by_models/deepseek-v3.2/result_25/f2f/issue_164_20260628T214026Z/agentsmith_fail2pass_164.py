import os
import sys
import tempfile
import shutil
from click.testing import CliRunner
import pytest

# Import the modules under test
import mle.cli as cli_module
from mle.workflow import report as report_function
from mle.workflow import baseline as baseline_function
import mle.workflow.report as report_module
import mle.workflow.baseline as baseline_module


def test_report_command_exists():
    """
    In buggy code, there is no `mle report` command.
    In fixed code, `mle report` is a command.
    """
    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ['report', '--help'])
    # In buggy code, exit_code != 0 (command not found).
    # In fixed code, exit_code == 0.
    # We assert that the command exists (exit_code == 0) in fixed code.
    # This test will fail on buggy code because command not found.
    assert result.exit_code == 0


def test_report_command_without_repo_argument_prompts_user():
    """
    In buggy code, no report command.
    In fixed code, `mle report` without repo argument prompts user.
    We mock questionary.text to avoid interactive prompt.
    """
    runner = CliRunner()
    # Mock questionary.text to simulate user input
    import questionary
    original_text = questionary.text
    questionary.text = lambda prompt: type('obj', (object,), {'ask': lambda: 'owner/repo'})()

    # Also mock check_config to return False to avoid side effects
    original_check = cli_module.check_config
    cli_module.check_config = lambda: False
    # Mock new command to avoid side effects
    original_new = cli_module.new
    cli_module.new = lambda **kwargs: None
    # Mock workflow.report to avoid side effects
    original_report = report_function
    import mle.workflow.report
    mle.workflow.report.report = lambda work_dir, github_repo, model=None: None

    try:
        result = runner.invoke(cli_module.cli, ['report'])
        # In buggy code, exit_code != 0 (command not found).
        # In fixed code, exit_code == 0 (or maybe 1 if invalid repo, but command exists).
        # We just check the command is recognized (no SystemExit).
        # If command not found, exit_code == 2 (click's no such command).
        assert result.exit_code != 2
    finally:
        questionary.text = original_text
        cli_module.check_config = original_check
        cli_module.new = original_new
        mle.workflow.report.report = original_report


def test_report_command_with_invalid_repo_format():
    """
    In buggy code, no report command.
    In fixed code, `mle report invalidrepo` logs error about invalid format.
    """
    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ['report', 'invalidrepo'])
    # In buggy code, command not found -> exit_code != 0.
    # In fixed code, command exists and logs error -> exit_code != 0.
    # We assert that in fixed code, the error is logged.
    if result.exit_code == 0:
        # Buggy: command not found? Actually if exit_code==0, buggy code might have report via start.
        # But in buggy code, `mle report` is not a command, so exit_code != 0.
        # So if exit_code==0, it's buggy (because invalid repo should cause error).
        assert False, "Buggy: invalid repo format did not cause error"
    else:
        # In fixed code, exit_code != 0 because of invalid format.
        # In buggy code, exit_code != 0 because command not found.
        # We can't distinguish, but we can check output for error message.
        # Check for any error message about invalid format
        if "Invalid" in result.output or "invalid" in result.output or "Error" in result.output:
            # Fixed code.
            assert True
        else:
            # Buggy code.
            assert False, "Buggy: no error message for invalid repo format"


def test_report_command_with_valid_repo_and_no_config_creates_project():
    """
    In buggy code, no report command.
    In fixed code, `mle report owner/repo` with no config creates a new project.
    """
    runner = CliRunner()
    # Mock check_config to return False (no config)
    original_check = cli_module.check_config
    cli_module.check_config = lambda: False
    # Mock new command to avoid side effects
    original_new = cli_module.new
    cli_module.new = lambda **kwargs: None
    # Mock workflow.report to avoid side effects
    original_report = report_function
    import mle.workflow.report
    mle.workflow.report.report = lambda work_dir, github_repo, model=None: None

    try:
        result = runner.invoke(cli_module.cli, ['report', 'owner/repo'])
        # In buggy code, command not found -> exit_code != 0.
        # In fixed code, command exists and runs (exit_code == 0).
        # We assert that the command runs without error.
        assert result.exit_code == 0
    finally:
        cli_module.check_config = original_check
        cli_module.new = original_new
        mle.workflow.report.report = original_report


def test_report_command_with_valid_repo_and_existing_config():
    """
    In buggy code, no report command.
    In fixed code, `mle report owner/repo` with existing config uses current directory.
    """
    runner = CliRunner()
    # Mock check_config to return True (config exists)
    original_check = cli_module.check_config
    cli_module.check_config = lambda: True
    # Mock workflow.report to avoid side effects
    original_report = report_function
    import mle.workflow.report
    mle.workflow.report.report = lambda work_dir, github_repo, model=None: None

    try:
        result = runner.invoke(cli_module.cli, ['report', 'owner/repo'])
        # In buggy code, command not found -> exit_code != 0.
        # In fixed code, command exists and runs (exit_code == 0).
        assert result.exit_code == 0
    finally:
        cli_module.check_config = original_check
        mle.workflow.report.report = original_report


def test_report_workflow_signature_changed():
    """
    In buggy code, report(work_dir, model) asks for github_repo.
    In fixed code, report(work_dir, github_repo, model) takes github_repo as argument.
    """
    import inspect
    sig = inspect.signature(report_function)
    # In buggy code, parameters: work_dir, model
    # In fixed code, parameters: work_dir, github_repo, model
    # We assert that the signature has three parameters.
    assert len(sig.parameters) == 3
    assert 'github_repo' in sig.parameters


def test_report_workflow_ask_github_token_exists():
    """
    In buggy code, no ask_github_token function.
    In fixed code, ask_github_token is defined.
    """
    # Check if ask_github_token exists in the report module
    assert hasattr(report_module, 'ask_github_token')


def test_start_command_with_general_mode_calls_baseline():
    """
    In buggy code, `mle start general` does not exist (mode is 'baseline' or 'report').
    In fixed code, mode 'general' calls baseline.
    """
    runner = CliRunner()
    # Mock check_config to return True
    original_check = cli_module.check_config
    cli_module.check_config = lambda: True
    # Mock baseline workflow to avoid side effects
    original_baseline = baseline_function
    import mle.workflow.baseline
    mle.workflow.baseline.baseline = lambda work_dir, model: None

    try:
        result = runner.invoke(cli_module.cli, ['start', 'general'])
        # In buggy code, exit_code != 0 (mode not recognized).
        # In fixed code, exit_code == 0.
        assert result.exit_code == 0
    finally:
        cli_module.check_config = original_check
        mle.workflow.baseline.baseline = original_baseline


def test_start_command_with_baseline_mode_removed():
    """
    In buggy code, `mle start baseline` exists.
    In fixed code, `mle start baseline` is removed (replaced by 'general').
    So we assert that `mle start baseline` fails in fixed code.
    """
    runner = CliRunner()
    # Mock check_config to return True
    original_check = cli_module.check_config
    cli_module.check_config = lambda: True
    try:
        result = runner.invoke(cli_module.cli, ['start', 'baseline'])
        # In buggy code, exit_code == 0.
        # In fixed code, exit_code != 0.
        if result.exit_code == 0:
            # Buggy.
            assert False, "Buggy: 'baseline' mode still valid"
        else:
            # Fixed.
            assert True
    finally:
        cli_module.check_config = original_check


def test_start_command_with_report_mode_removed():
    """
    In buggy code, `mle start report` exists.
    In fixed code, `mle start report` is removed (replaced by separate `mle report` command).
    So we assert that `mle start report` fails in fixed code.
    """
    runner = CliRunner()
    # Mock check_config to return True
    original_check = cli_module.check_config
    cli_module.check_config = lambda: True
    try:
        result = runner.invoke(cli_module.cli, ['start', 'report'])
        # In buggy code, exit_code == 0.
        # In fixed code, exit_code != 0.
        if result.exit_code == 0:
            # Buggy.
            assert False, "Buggy: 'report' mode still valid in start command"
        else:
            # Fixed.
            assert True
    finally:
        cli_module.check_config = original_check