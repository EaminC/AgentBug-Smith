from aider.models import Model

def test_bedrock_claude_45_support():
    """Test that Bedrock/Claude 4.5 model configuration is loaded correctly."""
    model_name = "bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    
    model = Model(model_name)
    
    assert model.edit_format == "diff", f"Expected edit_format='diff', got '{model.edit_format}'"
    assert model.weak_model_name == "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0"
    assert model.use_repo_map is True
    assert model.cache_control is True
    assert "thinking_tokens" in model.accepts_settings
