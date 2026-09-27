import tempfile
from pathlib import Path

from crewai.cli.utils import write_env_file


def test_write_env_file_uppercases_keys(tmp_path):
    env_vars = {
        "model": "azure/gpt-4o",
        "azure_api_key": "xx",
        "azure_api_base": "https://example.com",
        "azure_api_version": "2025-01-01-preview",
    }
    write_env_file(tmp_path, env_vars)
    env_file = tmp_path / ".env"
    content = env_file.read_text()
    # Verify every key appears in uppercase in the .env file
    for key in env_vars:
        expected_line = f"{key.upper()}="
        assert expected_line in content, f"Key '{key}' was not written as uppercase '{key.upper()}'"
    # Additional check: no lowercase key should be present
    lines = content.strip().splitlines()
    for line in lines:
        assert "=" in line, f"Malformed line: {line}"
        k, _ = line.split("=", 1)
        assert k == k.upper(), f"Key '{k}' is not uppercase in .env file"
