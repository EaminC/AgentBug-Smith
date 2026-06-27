import pytest
from aider.models import MODEL_SETTINGS


def test_vertex_ai_claude_models_in_model_settings():
    """Test that Vertex AI Claude models are properly configured in MODEL_SETTINGS.
    
    Issue #700: vertex_ai/claude_* models aren't in MODEL_SETTINGS
    When using e.g. vertex_ai/claude-3-5-sonnet@20240620, aider falls back to 
    whole-file editing with no repo map because the model isn't recognized.
    
    After the fix, these models should have use_repo_map=True and edit_format="diff".
    """
    # Map of model names to their expected weak model names
    expected_models = {
        "vertex_ai/claude-3-5-sonnet@20240620": "vertex_ai/claude-3-haiku@20240307",
        "vertex_ai/claude-3-opus@20240229": "vertex_ai/claude-3-haiku@20240307",
    }
    
    for model_name, expected_weak_model in expected_models.items():
        # Find settings for this model in MODEL_SETTINGS
        settings = None
        for s in MODEL_SETTINGS:
            if s.name == model_name:
                settings = s
                break
        
        assert settings is not None, (
            f"Model {model_name} should be in MODEL_SETTINGS"
        )
        assert settings.use_repo_map is True, (
            f"Model {model_name} should have use_repo_map=True"
        )
        assert settings.edit_format == "diff", (
            f"Model {model_name} should use diff edit format, not whole-file"
        )
        assert settings.weak_model_name == expected_weak_model, (
            f"Model {model_name} should have weak_model_name={expected_weak_model}"
        )
