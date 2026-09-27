import importlib
import pytest


def test_agentscope_web_studio_import():
    """
    Test that the agentscope.web.studio package can be imported successfully.

    This test will fail if the __init__.py file is missing in the agentscope.web.studio
    directory, causing an ImportError. After the fix (adding __init__.py), this test should pass.
    """
    # Try to import the module dynamically
    module_name = "agentscope.web.studio"
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        pytest.fail(f"Failed to import {module_name}: {e}")

    # Assert that the imported module has the expected __path__ attribute (indicating a package)
    assert hasattr(module, "__path__"), f"{module_name} should be a package with __path__ attribute"
    # Optionally check that __init__.py is recognized by checking the module file attribute
    # It should point to __init__.py or be a namespace package with __path__ but no __file__
    # We allow __file__ to be None for namespace packages, but here it should exist
    assert module.__file__ is not None, f"{module_name} should have a __file__ attribute pointing to __init__.py"
