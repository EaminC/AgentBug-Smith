import pytest
from mle.cli import cli, report
from mle.utils import system


def test_web_command_exists():
    """Test that the 'web' command was added to the CLI to support web display."""
    assert "web" in cli.commands, "The 'web' command should exist in the CLI"


def test_report_has_visualize_option():
    """Test that the report command has the --visualize option for combined web display."""
    param_names = [param.name for param in report.params]
    assert "visualize" in param_names, "The 'report' command should have a 'visualize' option"


def test_startup_web_function_exists():
    """Test that startup_web function exists in mle.utils.system for launching web server."""
    assert hasattr(system, "startup_web"), "system module should have 'startup_web' function"
    assert callable(system.startup_web), "startup_web should be callable"


def test_check_installed_function_exists():
    """Test that check_installed function exists in mle.utils.system for dependency checking."""
    assert hasattr(system, "check_installed"), "system module should have 'check_installed' function"
    assert callable(system.check_installed), "check_installed should be callable"
