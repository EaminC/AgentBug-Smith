import os
import sys
import pytest
import importlib
import mle.cli


def test_lancedb_memory_initialization_not_at_module_level():
    """
    Test that LanceDBMemory is not instantiated at module level in cli.py.
    In buggy version, `memory = LanceDBMemory(os.getcwd())` at module level
    causes TypeError because config may not be loaded.
    In fixed version, that line is removed and instantiation happens inside chat().
    """
    # In buggy version, the module import will raise TypeError because
    # LanceDBMemory.__init__ accesses config["platform"] before config is loaded.
    # In fixed version, the import succeeds because the line is moved inside chat().
    # We can detect this by checking if the module attribute 'memory' exists and is a LanceDBMemory.
    # However, we must ensure the test fails on buggy version and passes on fixed version.
    # The buggy version will raise TypeError during import (collection phase).
    # The fixed version will import without error.
    # Therefore, we can simply import mle.cli and assert that no TypeError occurs.
    # But we need to make the test fail on buggy version: we can try to access mle.cli.memory
    # and expect it to be None or not exist.
    # Actually, the buggy version will raise TypeError before the test runs (during collection).
    # That's fine for fail2pass: buggy version fails (collection error), fixed version passes.
    # However, we need a test that runs and asserts something.
    # Let's check if the module-level variable 'memory' is defined and is a LanceDBMemory.
    # In buggy version, it will be a LanceDBMemory instance (if import succeeded).
    # In fixed version, it should not exist (AttributeError) or be something else.
    # But we must avoid triggering the TypeError in buggy version during test execution.
    # The TypeError occurs during import of mle.cli, not during test execution.
    # So we can rely on the import already having happened (since we imported at top).
    # If the import succeeded (fixed version), we can proceed.
    # If the import failed (buggy version), the test collection would have failed already.
    # That's acceptable: buggy version fails at collection, fixed version passes.
    # However, the previous test run showed that after fix, the test failed because
    # `hasattr(mle.cli, 'memory')` raised UnboundLocalError due to mle being local variable.
    # That's because we imported mle.cli but not mle? Actually we imported mle.cli.
    # Let's fix: use the imported module directly.
    # We'll check if 'memory' attribute exists and is an instance of LanceDBMemory.
    # In buggy version, it will exist and be a LanceDBMemory (if import succeeded).
    # But import didn't succeed in buggy version because of TypeError.
    # So the test won't even run. That's fine.
    # To make the test run in both versions, we need to catch the TypeError during import.
    # But we cannot catch collection errors. Instead, we can dynamically import inside test.
    # Let's do: try to import mle.cli inside test; if TypeError, that's buggy version -> fail.
    # If import succeeds, then check for memory attribute.
    try:
        # Re-import to catch TypeError
        importlib.reload(mle.cli)
    except TypeError as e:
        if "'NoneType' object is not subscriptable" in str(e):
            # Buggy version: config is None at module level
            pytest.fail("LanceDBMemory instantiated at module level causes TypeError")
        else:
            raise
    # Fixed version: import succeeded
    # Now check that 'memory' is not a module-level LanceDBMemory instance.
    # It might not exist, or it might be something else (like a function).
    if hasattr(mle.cli, 'memory'):
        # If it exists, ensure it's not a LanceDBMemory instance.
        # But we need to import LanceDBMemory to check.
        from mle.utils import LanceDBMemory
        if isinstance(mle.cli.memory, LanceDBMemory):
            pytest.fail("LanceDBMemory instance still present at module level")
    # If we reach here, the test passes for fixed version.
