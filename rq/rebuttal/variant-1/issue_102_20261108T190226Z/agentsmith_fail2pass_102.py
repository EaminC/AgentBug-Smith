import importlib
import sys
import pytest

def test_import_agentscope_web_studio_package():
    """
    Test that the agentscope.web.studio package can be imported successfully.
    This will fail if __init__.py is missing in the agentscope.web.studio directory,
    causing ImportError or ModuleNotFoundError.
    """
    # Clear any cached modules related to agentscope.web.studio to ensure fresh import
    modules_to_clear = [name for name in sys.modules if name.startswith("agentscope.web.studio")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    # Attempt to import the package
    try:
        mod = importlib.import_module("agentscope.web.studio")
    except ModuleNotFoundError as e:
        pytest.fail(f"Failed to import 'agentscope.web.studio' package: {e}")

    # Assert that the imported module is a package (has __path__ attribute)
    assert hasattr(mod, "__path__"), "'agentscope.web.studio' should be a package with __path__ attribute"

    # Optionally, check that __init__.py is recognized by checking module file attribute
    # This is a proxy to confirm the package initialization file is present
    assert mod.__file__ is not None, "'agentscope.web.studio' module should have a __file__ attribute"

    # Import a submodule if any exist to confirm package usability (optional)
    # For example, if there's a known submodule, try importing it here
    # This part is skipped because the issue is about missing __init__.py blocking import

# This test will fail on the buggy tree because the missing __init__.py
# causes ModuleNotFoundError or ImportError when importing agentscope.web.studio.
# After applying the patch that adds __init__.py, this test should pass.
