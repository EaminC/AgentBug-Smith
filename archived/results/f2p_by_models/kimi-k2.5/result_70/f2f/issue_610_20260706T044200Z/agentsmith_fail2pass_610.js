from interpreter.code_interpreters.create_code_interpreter import create_code_interpreter

def test_powershell_language_support():
    """
    Test that PowerShell is supported as a code interpretation language.
    Regression test for issue #610 - PowerShell should be recognized and 
    instantiable without raising ValueError("Unknown or unsupported language").
    """
    # Before the fix: create_code_interpreter("powershell") raises 
    # ValueError: Unknown or unsupported language: powershell
    # After the fix: it should return a valid PowerShell interpreter instance
    interpreter = create_code_interpreter("powershell")
    
    # Verify we got a valid interpreter object back
    assert interpreter is not None
    
    # Verify it has the expected properties of a code interpreter
    assert hasattr(interpreter, 'file_extension')
    assert hasattr(interpreter, 'proper_name')
