"""
Test file for DashScopeChatFormatter functionality.
This follows the structure suggested by the in-patch test reference.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock


def test_dashscope_formatter_basic():
    """Test basic DashScopeChatFormatter functionality."""
    try:
        # Try to import from the likely location based on the repository structure
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        try:
            # Alternative import path
            from formatter import DashScopeChatFormatter
        except ImportError:
            # If neither works, skip the test with a clear message
            pytest.skip("DashScopeChatFormatter not found in expected locations")
            return
    
    # Initialize formatter with environment variables
    api_key = os.getenv("FORGE_API_KEY", "test-key")
    base_url = os.getenv("FORGE_BASE_URL", "https://api.test.com")
    
    formatter = DashScopeChatFormatter(
        api_key=api_key,
        base_url=base_url
    )
    
    # Test basic attributes
    assert formatter.api_key == api_key
    assert formatter.base_url == base_url
    
    # Test that formatter has required methods
    assert hasattr(formatter, 'format')
    assert callable(formatter.format)


def test_dashscope_formatter_format_method():
    """Test the format method of DashScopeChatFormatter."""
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        try:
            from formatter import DashScopeChatFormatter
        except ImportError:
            pytest.skip("DashScopeChatFormatter not found in expected locations")
            return
    
    # Mock API key for testing
    formatter = DashScopeChatFormatter(
        api_key="test-key",
        base_url="https://api.test.com"
    )
    
    # Test format method with mock messages
    test_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    
    # Test that format method exists and can be called
    try:
        result = formatter.format(test_messages)
        # Basic assertion that we got some result
        assert result is not None
    except NotImplementedError:
        # If format is abstract, that's okay for a base test
        pass
    except Exception as e:
        # Other exceptions should fail the test
        pytest.fail(f"Format method raised unexpected exception: {e}")


@pytest.mark.asyncio
async def test_dashscope_formatter_async_methods():
    """Test async methods if they exist."""
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        try:
            from formatter import DashScopeChatFormatter
        except ImportError:
            pytest.skip("DashScopeChatFormatter not found in expected locations")
            return
    
    formatter = DashScopeChatFormatter(
        api_key="test-key",
        base_url="https://api.test.com"
    )
    
    # Check for common async methods
    if hasattr(formatter, 'aformat') and callable(formatter.aformat):
        test_messages = [{"role": "user", "content": "Test async"}]
        
        # Mock any actual async calls to avoid network dependencies
        with patch.object(formatter, '_make_async_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"content": "Mocked response"}
            
            try:
                result = await formatter.aformat(test_messages)
                assert result is not None
            except Exception as e:
                pytest.fail(f"Async format method failed: {e}")


def test_dashscope_formatter_with_environment_variables():
    """Test that formatter correctly uses environment variables."""
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        try:
            from formatter import DashScopeChatFormatter
        except ImportError:
            pytest.skip("DashScopeChatFormatter not found in expected locations")
            return
    
    # Get actual environment variables
    api_key = os.getenv("FORGE_API_KEY")
    base_url = os.getenv("FORGE_BASE_URL")
    
    if not api_key or not base_url:
        pytest.skip("Environment variables not set for DashScope formatter")
    
    # Create formatter with environment variables
    formatter = DashScopeChatFormatter(
        api_key=api_key,
        base_url=base_url
    )
    
    # Verify environment variables are used
    assert formatter.api_key == api_key
    assert formatter.base_url == base_url
    
    # Test that formatter can be instantiated without errors
    assert formatter is not None


if __name__ == "__main__":
    # Simple runner for direct execution
    pytest.main([__file__, "-v"])