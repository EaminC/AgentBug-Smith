from agent.prompt.base import pmpt_chain_filename


def test_filename_prompt_requires_correct_extension():
    """
    Test that pmpt_chain_filename prompts the LLM to generate a filename 
    with the correct extension for the specified language.
    
    This prevents the bug where generated training files would incorrectly 
    use .csv extension instead of the appropriate code extension (e.g., .py).
    """
    prompt = pmpt_chain_filename("Python")
    
    # The fix ensures the prompt explicitly links the file extension to the language
    assert ".py for Python" in prompt, "Prompt should specify .py extension for Python language"
    assert "correct for the specified language" in prompt, "Prompt should require correct language-specific suffix"
