import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from autogpt.config.ai_config import AIConfig
from autogpt.config.config import Config
from autogpt.prompts.generator import PromptGenerator


def test_ai_config_includes_os_info_in_prompt_when_execute_local_commands_enabled():
    """Test that the AI prompt includes OS info when execute_local_commands is True."""
    # Create a config with execute_local_commands = True
    cfg = Config()
    cfg.execute_local_commands = True

    # Mock platform.system to return a known OS
    with patch("platform.system", return_value="Windows"):
        with patch("platform.platform", return_value="Windows-10-10.0.19045-SP0"):
            # Mock distro.name only if platform.system returns "Linux"
            with patch("distro.name", return_value="Ubuntu 22.04"):
                # Create AIConfig instance
                ai_config = AIConfig(
                    ai_name="TestAI",
                    ai_role="Test Role",
                    ai_goals=["Goal1", "Goal2"],
                )

                # Get the prompt string
                full_prompt = ai_config.construct_full_prompt()
                # Check that OS info is included
                assert "The OS you are running on is:" in full_prompt
                assert "Windows-10-10.0.19045-SP0" in full_prompt


def test_ai_config_excludes_os_info_in_prompt_when_execute_local_commands_disabled():
    """Test that the AI prompt does NOT include OS info when execute_local_commands is False."""
    # Create a config with execute_local_commands = False
    cfg = Config()
    cfg.execute_local_commands = False

    # Create AIConfig instance
    ai_config = AIConfig(
        ai_name="TestAI",
        ai_role="Test Role",
        ai_goals=["Goal1", "Goal2"],
    )

    # Get the prompt string
    full_prompt = ai_config.construct_full_prompt()
    # Check that OS info is NOT included
    assert "The OS you are running on is:" not in full_prompt


def test_ai_config_includes_linux_distro_when_platform_is_linux():
    """Test that the AI prompt uses distro.name(pretty=True) on Linux."""
    # Create a config with execute_local_commands = True
    cfg = Config()
    cfg.execute_local_commands = True

    # Mock platform.system to return "Linux"
    with patch("platform.system", return_value="Linux"):
        with patch("distro.name", return_value="Ubuntu 22.04"):
            # Create AIConfig instance
            ai_config = AIConfig(
                ai_name="TestAI",
                ai_role="Test Role",
                ai_goals=["Goal1", "Goal2"],
            )

            # Get the prompt string
            full_prompt = ai_config.construct_full_prompt()
            # Check that Linux distro info is included
            assert "The OS you are running on is:" in full_prompt
            assert "Ubuntu 22.04" in full_prompt


def test_ai_config_uses_platform_platform_for_non_linux():
    """Test that the AI prompt uses platform.platform(terse=True) for non-Linux OS."""
    # Create a config with execute_local_commands = True
    cfg = Config()
    cfg.execute_local_commands = True

    # Mock platform.system to return "Darwin" (macOS)
    with patch("platform.system", return_value="Darwin"):
        with patch("platform.platform", return_value="macOS-13.2.1-arm64-arm-64bit"):
            # Create AIConfig instance
            ai_config = AIConfig(
                ai_name="TestAI",
                ai_role="Test Role",
                ai_goals=["Goal1", "Goal2"],
            )

            # Get the prompt string
            full_prompt = ai_config.construct_full_prompt()
            # Check that platform.platform info is included
            assert "The OS you are running on is:" in full_prompt
            assert "macOS-13.2.1-arm64-arm-64bit" in full_prompt


def test_ai_config_prompt_includes_goals_and_role():
    """Ensure the prompt still contains the basic AI info (name, role, goals)."""
    cfg = Config()
    cfg.execute_local_commands = True

    with patch("platform.system", return_value="Windows"):
        with patch("platform.platform", return_value="Windows-10"):
            ai_config = AIConfig(
                ai_name="TestAI",
                ai_role="Test Role",
                ai_goals=["Goal1", "Goal2"],
            )

            full_prompt = ai_config.construct_full_prompt()
            # Check that basic AI info is present
            assert "You are TestAI, Test Role" in full_prompt
            assert "Goal1" in full_prompt
            assert "Goal2" in full_prompt
            # Also check OS info is included (since execute_local_commands is True)
            assert "The OS you are running on is:" in full_prompt
            assert "Windows-10" in full_prompt
