import pathlib

def test_philosophy_preprompt_respects_user_language_choice():
    """Test that the philosophy preprompt instructs the AI to use the language the user asks for."""
    philosophy_path = pathlib.Path(__file__).parent.parent / "gpt_engineer" / "preprompts" / "philosophy"
    
    content = philosophy_path.read_text()
    
    assert "Always use the programming language the user asks for" in content, \
        "Philosophy preprompt should contain instruction to use the programming language the user asks for"
