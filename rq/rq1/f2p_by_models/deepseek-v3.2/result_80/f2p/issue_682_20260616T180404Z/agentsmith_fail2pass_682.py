import pytest
from gpt_engineer.core.steps import Config, self_heal, get_platform_info, STEPS
from gpt_engineer.cli.main import main


def test_self_heal_config_exists():
    """Test that Config.SELF_HEAL enum value exists."""
    assert hasattr(Config, 'SELF_HEAL')
    assert Config.SELF_HEAL == "self_heal"


def test_self_heal_function_exists():
    """Test that self_heal function is defined."""
    assert callable(self_heal)


def test_get_platform_info_function_exists():
    """Test that get_platform_info function is defined."""
    assert callable(get_platform_info)


def test_get_platform_info_returns_string():
    """Test that get_platform_info returns a string with platform info."""
    result = get_platform_info()
    assert isinstance(result, str)
    assert "Python Version:" in result
    assert "OS:" in result


def test_self_heal_in_steps_dict():
    """Test that self_heal is registered in STEPS dictionary."""
    assert Config.SELF_HEAL in STEPS
    assert self_heal in STEPS[Config.SELF_HEAL]


def test_self_heal_step_list():
    """Test that SELF_HEAL step list contains self_heal function."""
    steps = STEPS[Config.SELF_HEAL]
    assert len(steps) > 0
    assert steps[0] == self_heal
