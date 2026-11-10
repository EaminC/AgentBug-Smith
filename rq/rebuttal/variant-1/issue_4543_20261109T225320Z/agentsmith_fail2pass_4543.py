import pytest
import yaml
from pathlib import Path

def test_bedrock_claude_sonnet_4_5_model_in_model_settings():
    # Load the model-settings.yml file from the resources directory
    model_settings_path = Path(__file__).parent.parent / "aider" / "resources" / "model-settings.yml"
    assert model_settings_path.exists(), f"model-settings.yml not found at {model_settings_path}"

    with model_settings_path.open("r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    # content is expected to be a list of dicts, each dict describing a model config
    assert isinstance(content, list), "model-settings.yml root element is not a list"

    # Search for the new model entry by name
    target_name = "bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    found = None
    for entry in content:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") == target_name:
            found = entry
            break

    assert found is not None, f"Model entry '{target_name}' not found in model-settings.yml"

    # Validate some expected keys and values in the model entry
    assert found.get("edit_format") == "diff"
    assert found.get("weak_model_name") == "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0"
    assert found.get("use_repo_map") is True
    assert found.get("examples_as_sys_msg") is False
    extra_params = found.get("extra_params")
    assert isinstance(extra_params, dict)
    extra_headers = extra_params.get("extra_headers")
    assert isinstance(extra_headers, dict)
    # Check that the expected header keys are present
    expected_headers = [
        "anthropic-beta"
    ]
    for header in expected_headers:
        assert header in extra_headers
    # Check max_tokens is 64000
    assert extra_params.get("max_tokens") == 64000
    # Check cache_control is True
    assert found.get("cache_control") is True
    # Check editor_model_name matches the name
    assert found.get("editor_model_name") == target_name
    # Check editor_edit_format is editor-diff
    assert found.get("editor_edit_format") == "editor-diff"
    # Check accepts_settings list contains "thinking_tokens"
    accepts_settings = found.get("accepts_settings")
    assert isinstance(accepts_settings, list)
    assert "thinking_tokens" in accepts_settings
