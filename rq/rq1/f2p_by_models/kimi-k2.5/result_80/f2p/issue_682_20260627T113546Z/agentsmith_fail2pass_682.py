import inspect
from pathlib import Path

from gpt_engineer.core.steps import (
    Config,
    STEPS,
    self_heal,
    get_platform_info,
    MAX_SELF_HEAL_ATTEMPTS,
    ASSUME_WORKING_TIMEOUT,
)


def test_self_heal_config_exists():
    """Test that SELF_HEAL config was added to the Config enum."""
    assert hasattr(Config, 'SELF_HEAL')
    assert Config.SELF_HEAL.value == 'self_heal'


def test_self_heal_step_registered():
    """Test that SELF_HEAL config maps to the self_heal function."""
    assert Config.SELF_HEAL in STEPS
    assert STEPS[Config.SELF_HEAL] == [self_heal]


def test_self_heal_function_exists():
    """Test that self_heal function is importable and callable."""
    assert callable(self_heal)
    sig = inspect.signature(self_heal)
    params = list(sig.parameters.keys())
    assert 'ai' in params
    assert 'dbs' in params


def test_get_platform_info_function():
    """Test that get_platform_info returns expected platform information."""
    assert callable(get_platform_info)
    info = get_platform_info()
    assert isinstance(info, str)
    assert "Python Version:" in info
    assert "OS:" in info


def test_self_heal_constants():
    """Test that self-healing constants are defined correctly."""
    assert MAX_SELF_HEAL_ATTEMPTS == 2
    assert ASSUME_WORKING_TIMEOUT == 30


def test_file_format_fix_preprompt_exists():
    """Test that the file_format_fix preprompt file was created."""
    preprompt_path = Path(__file__).parent.parent / "gpt_engineer" / "preprompts" / "file_format_fix"
    assert preprompt_path.exists()
    content = preprompt_path.read_text()
    assert "Please fix any errors" in content
    assert "FILENAME" in content
    assert "```" in content
