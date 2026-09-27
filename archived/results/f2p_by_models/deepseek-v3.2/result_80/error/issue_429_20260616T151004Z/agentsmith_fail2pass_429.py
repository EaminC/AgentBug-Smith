import os
import pytest
from unittest.mock import patch, MagicMock
from valuecell.adapters.models.factory import ModelFactory, DashScopeProvider
from valuecell.config.manager import ConfigManager


def test_dashscope_provider_registration():
    """
    Test that DashScopeProvider is correctly registered in ModelFactory.
    This test should pass after the fix is applied.
    """
    # Check that DashScopeProvider is available
    try:
        from valuecell.adapters.models.factory import DashScopeProvider
    except ImportError:
        pytest.fail("DashScopeProvider not available")

    # Verify DashScopeProvider is registered in ModelFactory
    assert "dashscope" in ModelFactory._provider_classes
    assert ModelFactory._provider_classes["dashscope"] is DashScopeProvider


def test_dashscope_provider_creation():
    """
    Test that DashScopeProvider can create models correctly.
    """
    # Create mock config
    mock_config = MagicMock()
    mock_config.name = "DashScope"
    mock_config.provider_type = "dashscope"
    mock_config.default_model = "qwen-max"
    mock_config.parameters = {"temperature": 0.7, "max_tokens": 16384}
    mock_config.base_url = None
    mock_config.api_key = "test-key"
    mock_config.default_embedding_model = "text-embedding-v3"
    mock_config.embedding_parameters = {"dimensions": 1536}

    # Create provider instance
    provider = DashScopeProvider(mock_config)

    # Mock the underlying DashScope client to avoid API calls
    with patch('agno.models.dashscope.DashScope') as mock_dashscope_class:
        mock_dashscope_instance = MagicMock()
        mock_dashscope_class.return_value = mock_dashscope_instance

        # Test model creation
        model = provider.create_model(model_id="qwen-max")
        assert model is mock_dashscope_instance
        mock_dashscope_class.assert_called_once_with(
            id="qwen-max",
            api_key="test-key",
            base_url=None,
            temperature=0.7,
            max_tokens=16384,
            top_p=None,
        )

    # Test embedder creation
    with patch('agno.knowledge.embedder.openai.OpenAIEmbedder') as mock_embedder_class:
        mock_embedder_instance = MagicMock()
        mock_embedder_class.return_value = mock_embedder_instance

        embedder = provider.create_embedder(model_id="text-embedding-v3")
        assert embedder is mock_embedder_instance
        mock_embedder_class.assert_called_once_with(
            id="text-embedding-v3",
            api_key="test-key",
            base_url=None,
            dimensions=1536,
            encoding_format=None,
        )


def test_model_factory_with_dashscope():
    """
    Test that ModelFactory can create DashScope models after registration.
    """
    # Mock config manager
    mock_config = MagicMock(spec=ConfigManager)
    mock_provider_config = MagicMock()
    mock_provider_config.name = "DashScope"
    mock_provider_config.provider_type = "dashscope"
    mock_provider_config.default_model = "qwen-max"
    mock_provider_config.parameters = {"temperature": 0.7}
    mock_provider_config.base_url = None
    mock_provider_config.api_key = "test-key"
    
    mock_config.get_provider_config.return_value = mock_provider_config

    # Create factory
    factory = ModelFactory(config_manager=mock_config)

    # Verify dashscope is available
    assert "dashscope" in factory._provider_classes

    # Test creating a model with mocked dependencies
    with patch('agno.models.dashscope.DashScope') as mock_dashscope_class:
        mock_dashscope_instance = MagicMock()
        mock_dashscope_class.return_value = mock_dashscope_instance

        model = factory.create_model(provider_type="dashscope", model_id="qwen-max")
        assert model is mock_dashscope_instance


def test_dashscope_provider_with_environment_variables():
    """
    Test that DashScopeProvider uses environment variables when config doesn't have API key.
    """
    # Create config without API key
    mock_config = MagicMock()
    mock_config.name = "DashScope"
    mock_config.provider_type = "dashscope"
    mock_config.default_model = "qwen-max"
    mock_config.parameters = {"temperature": 0.7}
    mock_config.base_url = None
    mock_config.api_key = None  # No API key in config
    mock_config.default_embedding_model = "text-embedding-v3"
    mock_config.embedding_parameters = {}

    provider = DashScopeProvider(mock_config)

    # Set environment variable
    os.environ["DASHSCOPE_API_KEY"] = "env-test-key"

    try:
        with patch('agno.models.dashscope.DashScope') as mock_dashscope_class:
            mock_dashscope_instance = MagicMock()
            mock_dashscope_class.return_value = mock_dashscope_instance

            model = provider.create_model(model_id="qwen-max")
            
            # Should use environment variable
            mock_dashscope_class.assert_called_once()
            call_kwargs = mock_dashscope_class.call_args[1]
            assert call_kwargs["api_key"] == "env-test-key"
    finally:
        # Clean up environment variable
        os.environ.pop("DASHSCOPE_API_KEY", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])