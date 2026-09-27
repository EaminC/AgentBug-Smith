import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the necessary modules
try:
    from agentscope.service.mcp_manager import MCPManager
    from agentscope.service import ServiceToolkit
    HAS_AGENTSCOPE = True
except ImportError:
    HAS_AGENTSCOPE = False


@pytest.mark.skipif(not HAS_AGENTSCOPE, reason="agentscope not installed")
@pytest.mark.asyncio
async def test_mcp_manager_streamable_http_support():
    """Test that MCPManager correctly handles streamable_http type."""
    
    # Create a streamable_http configuration
    config = {
        "type": "streamable_http",
        "url": "http://127.0.0.1:8001/streamable_http_app/mcp/",
    }
    
    # Create the manager
    manager = MCPManager(config)
    
    # Mock the mcp module and its clients
    mock_mcp = MagicMock()
    mock_mcp.client = MagicMock()
    
    # Create mock clients
    mock_mcp.client.sse = MagicMock()
    mock_mcp.client.sse.sse_client = AsyncMock()
    mock_mcp.client.stdio = MagicMock()
    mock_mcp.client.stdio.stdio_client = AsyncMock()
    mock_mcp.client.streamable_http = MagicMock()
    mock_mcp.client.streamable_http.streamablehttp_client = AsyncMock()
    
    # Mock ClientSession
    mock_mcp.ClientSession = AsyncMock()
    
    # Create mock streams
    mock_streams = (AsyncMock(), AsyncMock())
    mock_mcp.client.streamable_http.streamablehttp_client.return_value.__aenter__.return_value = mock_streams
    
    # Mock session
    mock_session = AsyncMock()
    mock_mcp.ClientSession.return_value.__aenter__.return_value = mock_session
    
    # Patch the mcp module
    with patch.dict('sys.modules', {'mcp': mock_mcp}):
        with patch('agentscope.service.mcp_manager.mcp', mock_mcp):
            with patch('agentscope.service.mcp_manager.streamablehttp_client', 
                      mock_mcp.client.streamable_http.streamablehttp_client):
                with patch('agentscope.service.mcp_manager.sse_client', 
                          mock_mcp.client.sse.sse_client):
                    with patch('agentscope.service.mcp_manager.stdio_client', 
                              mock_mcp.client.stdio.stdio_client):
                        
                        # Re-import to use mocked module
                        import importlib
                        import agentscope.service.mcp_manager as mcp_mod
                        importlib.reload(mcp_mod)
                        from agentscope.service.mcp_manager import MCPManager
                        
                        # Create new manager with mocked dependencies
                        manager = MCPManager(config)
                        
                        # Initialize the manager
                        await manager.initialize()
                        
                        # Verify that streamablehttp_client was called
                        assert mock_mcp.client.streamable_http.streamablehttp_client.called
                        
                        # Verify the URL passed to streamablehttp_client
                        call_args = mock_mcp.client.streamable_http.streamablehttp_client.call_args
                        assert call_args[1]['url'] == config["url"]


@pytest.mark.skipif(not HAS_AGENTSCOPE, reason="agentscope not installed")
@pytest.mark.asyncio
async def test_mcp_manager_sse_still_works():
    """Test that SSE type still works."""
    
    config = {
        "type": "sse",
        "url": "http://127.0.0.1:8001/sse_app/sse",
    }
    
    manager = MCPManager(config)
    
    # Mock the mcp module
    mock_mcp = MagicMock()
    mock_mcp.client = MagicMock()
    mock_mcp.client.sse = MagicMock()
    mock_mcp.client.sse.sse_client = AsyncMock()
    mock_mcp.client.stdio = MagicMock()
    mock_mcp.client.stdio.stdio_client = AsyncMock()
    mock_mcp.client.streamable_http = MagicMock()
    mock_mcp.client.streamable_http.streamablehttp_client = AsyncMock()
    
    mock_mcp.ClientSession = AsyncMock()
    
    mock_streams = (AsyncMock(), AsyncMock())
    mock_mcp.client.sse.sse_client.return_value.__aenter__.return_value = mock_streams
    mock_session = AsyncMock()
    mock_mcp.ClientSession.return_value.__aenter__.return_value = mock_session
    
    with patch.dict('sys.modules', {'mcp': mock_mcp}):
        with patch('agentscope.service.mcp_manager.mcp', mock_mcp):
            with patch('agentscope.service.mcp_manager.sse_client', 
                      mock_mcp.client.sse.sse_client):
                with patch('agentscope.service.mcp_manager.streamablehttp_client', 
                          mock_mcp.client.streamable_http.streamablehttp_client):
                    with patch('agentscope.service.mcp_manager.stdio_client', 
                              mock_mcp.client.stdio.stdio_client):
                        
                        import importlib
                        import agentscope.service.mcp_manager as mcp_mod
                        importlib.reload(mcp_mod)
                        from agentscope.service.mcp_manager import MCPManager
                        
                        manager = MCPManager(config)
                        await manager.initialize()
                        
                        # Verify that sse_client was called
                        assert mock_mcp.client.sse.sse_client.called
                        
                        # Verify the URL passed to sse_client
                        call_args = mock_mcp.client.sse.sse_client.call_args
                        assert call_args[1]['url'] == config["url"]


@pytest.mark.skipif(not HAS_AGENTSCOPE, reason="agentscope not installed")
def test_service_toolkit_adds_streamable_http_server():
    """Test that ServiceToolkit can add streamable_http servers."""
    
    toolkit = ServiceToolkit()
    
    # Add a streamable_http server
    toolkit.add_mcp_servers({
        "mcpServers": {
            "test-server": {
                "type": "streamable_http",
                "url": "http://127.0.0.1:8001/streamable_http_app/mcp/",
            },
        },
    })
    
    # Verify the server was added
    assert "test-server" in toolkit._mcp_managers
    manager = toolkit._mcp_managers["test-server"]
    assert isinstance(manager, MCPManager)
    
    # Check the config
    assert manager.config["type"] == "streamable_http"
    assert manager.config["url"] == "http://127.0.0.1:8001/streamable_http_app/mcp/"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])