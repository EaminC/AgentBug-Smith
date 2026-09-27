"""
Test file for OpenAI provider functionality.
This test should fail before the patch and pass after the patch.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Try to import the actual modules from the project
try:
    # Try to import OpenAIProvider if it exists
    from valuecell.adapters.models.factory import ModelFactory, OpenAIProvider
    from valuecell.config.manager import ConfigManager
    HAS_OPENAI_PROVIDER = True
except ImportError:
    HAS_OPENAI_PROVIDER = False

try:
    from valuecell.utils.model import model_should_use_json_mode
    HAS_MODEL_UTILS = True
except ImportError:
    HAS_MODEL_UTILS = False


def test_openai_provider_exists():
    """Test that OpenAIProvider class exists in the codebase."""
    # This test will fail before the patch (when OpenAIProvider is missing)
    # and pass after the patch (when OpenAIProvider is added)
    assert HAS_OPENAI_PROVIDER, "OpenAIProvider should be defined in valuecell.adapters.models.factory"


def test_openai_in_model_factory():
    """Test that OpenAI provider is registered in ModelFactory."""
    if not HAS_OPENAI_PROVIDER:
        pytest.skip("OpenAIProvider not available")
    
    # Check if 'openai' is in ModelFactory providers
    # Before patch: this will fail
    # After patch: this should pass
    assert "openai" in ModelFactory._providers, "'openai' should be registered in ModelFactory"
    
    # Also verify it points to the correct class
    assert ModelFactory._providers["openai"] == OpenAIProvider, "OpenAI provider should map to OpenAIProvider class"


def test_openai_provider_creation():
    """Test basic OpenAIProvider creation."""
    if not HAS_OPENAI_PROVIDER:
        pytest.skip("OpenAIProvider not available")
    
    # Create a mock config
    mock_config = MagicMock()
    mock_config.name = "OpenAI"
    mock_config.provider_type = "openai"
    mock_config.default_model = "gpt-4"
    mock_config.default_embedding_model = "text-embedding-ada-002"
    mock_config.api_key = "test-key"
    mock_config.parameters = {"temperature": 0.7}
    mock_config.embedding_parameters = {}
    
    # Create provider instance
    provider = OpenAIProvider(mock_config)
    
    # Verify basic attributes
    assert provider.config == mock_config
    assert provider.config.name == "OpenAI"
    assert provider.config.provider_type == "openai"


def test_openai_in_config_manager():
    """Test that ConfigManager includes OpenAI in preferred providers."""
    if not HAS_OPENAI_PROVIDER:
        pytest.skip("OpenAIProvider not available")
    
    # Create a ConfigManager instance
    config_manager = ConfigManager()
    
    # Get available providers
    providers = config_manager.get_model_providers()
    
    # Check if 'openai' is in the providers
    # Before patch: this will likely fail
    # After patch: this should pass
    assert "openai" in providers, "'openai' should be available in ConfigManager providers"


def test_model_json_mode_for_openai():
    """Test that model_should_use_json_mode returns True for OpenAI models."""
    if not HAS_MODEL_UTILS:
        pytest.skip("model_should_use_json_mode not available")
    
    # Create a mock OpenAI model
    mock_model = MagicMock()
    
    # Set attributes that would identify it as an OpenAI model
    # The actual implementation might check different attributes
    mock_model.provider = "openai"
    mock_model.name = "gpt-4"
    
    # Test the function
    result = model_should_use_json_mode(mock_model)
    
    # Before patch: might return False for OpenAI models
    # After patch: should return True for OpenAI models
    # We'll assert based on what the fixed code should do
    assert result is True, "OpenAI models should use JSON mode"


def test_openai_provider_methods():
    """Test that OpenAIProvider has required methods."""
    if not HAS_OPENAI_PROVIDER:
        pytest.skip("OpenAIProvider not available")
    
    # Create a mock config
    mock_config = MagicMock()
    mock_config.name = "OpenAI"
    mock_config.provider_type = "openai"
    mock_config.default_model = "gpt-4"
    mock_config.default_embedding_model = "text-embedding-ada-002"
    mock_config.api_key = "test-key"
    mock_config.parameters = {"temperature": 0.7}
    mock_config.embedding_parameters = {}
    
    provider = OpenAIProvider(mock_config)
    
    # Check that required methods exist
    assert hasattr(provider, 'create_model'), "OpenAIProvider should have create_model method"
    assert hasattr(provider, 'create_embedder'), "OpenAIProvider should have create_embedder method"
    
    # Test create_model with mock
    with patch('agno.models.openai.OpenAIChat') as MockOpenAIChat:
        mock_instance = MagicMock()
        MockOpenAIChat.return_value = mock_instance
        
        model = provider.create_model()
        
        # Verify the method was called
        MockOpenAIChat.assert_called_once()
        assert model == mock_instance
    
    # Test create_embedder with mock  
    with patch('agno.knowledge.embedder.openai.OpenAIEmbedder') as MockOpenAIEmbedder:
        mock_instance = MagicMock()
        MockOpenAIEmbedder.return_value = mock_instance
        
        embedder = provider.create_embedder()
        
        # Verify the method was called
        MockOpenAIEmbedder.assert_called_once()
        assert embedder == mock_instance


if __name__ == "__main__":
    # Run tests directly if needed
    pytest.main([__file__, "-v"])