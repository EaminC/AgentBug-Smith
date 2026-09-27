import os
import sys
import yaml
from pathlib import Path

def test_bedrock_claude_4_5_support():
    """Check that the model settings YAML includes the new Bedrock/Claude 4.5 entry."""
    # Path to the model-settings.yml file in the aider resources
    model_settings_path = Path(__file__).parent.parent / "aider" / "resources" / "model-settings.yml"
    assert model_settings_path.exists(), f"Expected file not found: {model_settings_path}"

    # Load the YAML content
    with open(model_settings_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # The data is a list of model definitions
    assert isinstance(data, list), "model-settings.yml should contain a list of model definitions"

    # Look for the specific model name mentioned in the issue
    target_name = "bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    found = False
    for entry in data:
        if isinstance(entry, dict) and entry.get("name") == target_name:
            found = True
            # Verify some expected fields from the patch
            assert entry.get("edit_format") == "diff"
            assert entry.get("weak_model_name") == "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0"
            assert entry.get("use_repo_map") is True
            assert entry.get("examples_as_sys_msg") is False
            extra_params = entry.get("extra_params", {})
            assert isinstance(extra_params, dict)
            extra_headers = extra_params.get("extra_headers", {})
            # The extra_headers may be a dict or a string; in the patch it's a dict with anthropic-beta key
            # Actually looking at the patch, extra_headers is a dict with anthropic-beta as a key
            # but the value is a string with comma-separated values.
            # We'll just check that the key exists.
            assert "anthropic-beta" in extra_headers
            assert extra_params.get("max_tokens") == 64000
            assert entry.get("cache_control") is True
            assert entry.get("editor_model_name") == target_name
            assert entry.get("editor_edit_format") == "editor-diff"
            accepts_settings = entry.get("accepts_settings", [])
            assert isinstance(accepts_settings, list)
            assert "thinking_tokens" in accepts_settings
            break

    # This assertion must fail on buggy code (missing entry) and pass after patch (entry added)
    assert found, f"Model '{target_name}' not found in model-settings.yml. The patch should have added it."
