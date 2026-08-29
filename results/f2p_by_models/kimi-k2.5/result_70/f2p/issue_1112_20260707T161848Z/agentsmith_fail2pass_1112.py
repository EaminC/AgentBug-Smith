import pytest
from gpt_engineer.core.ai import AI


def test_gpt_4_turbo_vision_support():
    """
    Regression test for issue #1112: Missing support for vision capabilities in gpt-4-turbo.
    
    Before the fix: gpt-4-turbo was not recognized as a vision model because the code
    only checked if "vision" was substring of model_name.
    
    After the fix: gpt-4-turbo and gpt-4-turbo-2024-04-09 are correctly identified as
    vision-capable models, while gpt-4-turbo-preview (which contains "preview") is not.
    """
    # Store original method to restore after test
    original_create_chat_model = AI._create_chat_model
    
    # Mock _create_chat_model to avoid requiring API keys or network calls
    AI._create_chat_model = lambda self: None
    
    try:
        # Test that gpt-4-turbo is recognized as a vision model (main regression test)
        ai_turbo = AI(model_name="gpt-4-turbo")
        assert ai_turbo.vision is True, "gpt-4-turbo should have vision=True"
        
        # Test that dated gpt-4-turbo variant is also recognized
        ai_turbo_dated = AI(model_name="gpt-4-turbo-2024-04-09")
        assert ai_turbo_dated.vision is True, "gpt-4-turbo-2024-04-09 should have vision=True"
        
        # Test that gpt-4-turbo-preview is NOT a vision model (contains "preview")
        ai_turbo_preview = AI(model_name="gpt-4-turbo-preview")
        assert ai_turbo_preview.vision is False, "gpt-4-turbo-preview should have vision=False"
        
        # Test backward compatibility with existing vision models
        ai_vision_preview = AI(model_name="gpt-4-vision-preview")
        assert ai_vision_preview.vision is True, "gpt-4-vision-preview should have vision=True"
        
    finally:
        # Restore original method
        AI._create_chat_model = original_create_chat_model
