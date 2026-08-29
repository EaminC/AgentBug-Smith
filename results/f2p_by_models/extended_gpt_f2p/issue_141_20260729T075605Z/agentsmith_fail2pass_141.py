import os
import json
import pytest

def test_ollama_model_config_key():
    """
    Test that the ollama model config JSON files use 'model_name' as the key
    instead of 'model' for specifying the model name.
    This test reads the JSON config file and asserts that no config uses 'model'
    key, and all use 'model_name' key.
    """

    # The path to the ollama model config JSON file
    config_path = os.path.join('scripts', 'ollama', 'model_config.json')

    # Read the JSON config file
    with open(config_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)

    # For each config dict, check keys
    for config in configs:
        # The buggy code has 'model' key instead of 'model_name'
        # So the test should fail if 'model' key is present
        assert 'model' not in config, (
            f"Config {config.get('config_name', '')} contains 'model' key instead of 'model_name'"
        )
        # The correct key 'model_name' must be present
        assert 'model_name' in config, (
            f"Config {config.get('config_name', '')} does not contain 'model_name' key"
        )
