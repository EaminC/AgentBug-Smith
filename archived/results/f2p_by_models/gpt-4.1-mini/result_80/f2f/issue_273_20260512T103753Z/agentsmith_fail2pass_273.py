import os
import pytest
from mle.utils.memory import LanceDBMemory


def test_lancedbmemory_init_with_empty_config():
    """
    This test triggers the LanceDBMemory initialization which previously failed
    when config was None and accessed like a dict.
    The bug was that LanceDBMemory.__init__ did:
        if config["platform"] == "OpenAI":
    without checking if config is None.
    After the fix, this should not raise TypeError.
    """
    cwd = os.getcwd()
    # The test expects LanceDBMemory to initialize without TypeError
    # even if config is None or missing keys.
    # It will raise other errors if something else is wrong,
    # but not TypeError from NoneType subscript.
    memory = LanceDBMemory(cwd)
    assert memory is not None


def test_lancedbmemory_init_does_not_fail_on_first_setup():
    """
    Simulate first time setup by ensuring no config file exists in cwd.
    LanceDBMemory should not fail with TypeError.
    """
    cwd = os.getcwd()
    config_path = os.path.join(cwd, "config.yaml")
    backup_path = None
    restored = False

    # Backup config.yaml if it exists
    if os.path.exists(config_path):
        backup_path = config_path + ".bak"
        os.rename(config_path, backup_path)
        restored = True

    try:
        memory = LanceDBMemory(cwd)
        assert memory is not None
    finally:
        # Restore config.yaml if it was backed up
        if restored:
            os.rename(backup_path, config_path)