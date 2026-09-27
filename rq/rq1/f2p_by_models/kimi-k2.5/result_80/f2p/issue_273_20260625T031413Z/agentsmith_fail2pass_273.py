import sys

def test_cli_import_without_config():
    """
    Test that mle.cli can be imported without an existing config file.
    
    Regression test for issue #273: LanceDB error when first setting up a project.
    The bug occurred because LanceDBMemory was instantiated at module level in cli.py,
    which failed with TypeError: 'NoneType' object is not subscriptable when 
    attempting to access config["platform"] (config was None during first-time setup).
    
    The fix moves the LanceDBMemory initialization inside the chat() function,
    deferring it until the command is actually invoked.
    """
    # Clear any cached mle modules to force a fresh import
    modules_to_clear = [key for key in sys.modules.keys() if key.startswith('mle')]
    for mod in modules_to_clear:
        del sys.modules[mod]
    
    # This import should succeed even when no config file exists.
    # On the buggy version, this raises:
    # TypeError: 'NoneType' object is not subscriptable
    # because cli.py immediately calls LanceDBMemory(os.getcwd()) at module level.
    import mle.cli
    
    # Verify the module loaded successfully and chat command exists
    assert hasattr(mle.cli, 'chat')
