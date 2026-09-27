import pytest
import yaml
import os

MODEL_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aider", "resources", "model-settings.yml")

def test_bedrock_claude_sonnet_4_5_in_model_settings():
    """
    Test that the model-settings.yml includes the new model configuration for
    bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0 as specified in the patch.
    This test will fail on the buggy codebase (missing entry) and pass after the fix.
    """
    with open(MODEL_SETTINGS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # data is expected to be a list of dicts
    assert isinstance(data, list), "model-settings.yml root should be a list"

    # Find the entry with the new model name
    target_name = "bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    found = None
    for entry in data:
        if isinstance(entry, dict) and entry.get("name") == target_name:
            found = entry
            break

    assert found is not None, f"Model '{target_name}' not found in model-settings.yml"

    # Check some key expected fields from the patch
    assert found.get("edit_format") == "diff"
    assert found.get("weak_model_name") == "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0"
    assert found.get("use_repo_map") is True
    assert found.get("examples_as_sys_msg") is False
    assert "extra_params" in found
    extra_params = found["extra_params"]
    assert "extra_headers" in extra_params
    headers = extra_params["extra_headers"]
    assert "anthropic-beta" in headers
    assert "max_tokens" in extra_params and extra_params["max_tokens"] == 64000
    assert found.get("cache_control") is True
    assert found.get("editor_model_name") == target_name
    assert found.get("editor_edit_format") == "editor-diff"
    assert found.get("accepts_settings") == ["thinking_tokens"]
