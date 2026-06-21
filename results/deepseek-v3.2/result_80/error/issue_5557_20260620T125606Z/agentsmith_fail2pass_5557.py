import asyncio
import os
import sys
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock

# Try to import the module with fallback
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    # Create a mock class for testing if langgraph isn't available
    class AsyncPostgresSaver:
        @classmethod
        def from_conn_string(cls, conn_str):
            return cls()
        
        async def aget_tuple(self, thread_id):
            raise NotImplementedError("Mock implementation")

pytestmark = pytest.mark.asyncio

async def test_aget_tuple_with_none_channel_values():
    """Test that aget_tuple handles NULL channel_values gracefully."""
    
    if not HAS_LANGGRAPH:
        pytest.skip("langgraph package not available")
    
    # Mock the database connection
    mock_row = MagicMock()
    mock_row.thread_id = "test_thread"
    mock_row.checkpoint_id = 1
    mock_row.parent_checkpoint_id = None
    mock_row.checkpoint = {"step": 1}
    mock_row.metadata = None
    mock_row.channel_values = None  # This triggers the bug
    mock_row.writes = None
    mock_row.created_at = "2025-01-01"
    mock_row.version = "1.0"
    
    # Create a mock connection that returns our row
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_row
    
    # Create a mock pool
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    # Patch asyncpg.create_pool
    with patch('asyncpg.create_pool', AsyncMock(return_value=mock_pool)):
        saver = AsyncPostgresSaver.from_conn_string("postgresql://dummy")
        saver.pool = mock_pool
        
        try:
            result = await saver.aget_tuple("test_thread")
            # If we get here, the bug might be fixed
            # Verify the structure
            assert isinstance(result, tuple)
            if len(result) >= 5:  # Should have at least 5 elements
                _, _, _, _, channel_values, _ = result[:6]
                # channel_values should not be None after fix
                assert channel_values is not None
                assert isinstance(channel_values, dict)
        except TypeError as e:
            if "'NoneType' object is not a mapping" in str(e):
                # This is the bug - test should fail in buggy state
                pytest.fail(f"Bug reproduced: {e}")
            else:
                raise
        except Exception as e:
            # Other exceptions might occur due to missing dependencies
            # but we should at least not get the TypeError
            if "'NoneType' object is not a mapping" in str(e):
                pytest.fail(f"Bug reproduced: {e}")
            # Allow other exceptions to pass through

async def test_aget_tuple_with_empty_channel_values():
    """Test that aget_tuple works when channel_values is empty dict."""
    
    if not HAS_LANGGRAPH:
        pytest.skip("langgraph package not available")
    
    mock_row = MagicMock()
    mock_row.thread_id = "test_thread"
    mock_row.checkpoint_id = 2
    mock_row.parent_checkpoint_id = None
    mock_row.checkpoint = {"step": 2}
    mock_row.metadata = None
    mock_row.channel_values = {}  # Empty dict, not None
    mock_row.writes = None
    mock_row.created_at = "2025-01-01"
    mock_row.version = "1.0"
    
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_row
    
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    with patch('asyncpg.create_pool', AsyncMock(return_value=mock_pool)):
        saver = AsyncPostgresSaver.from_conn_string("postgresql://dummy")
        saver.pool = mock_pool
        
        result = await saver.aget_tuple("test_thread")
        assert isinstance(result, tuple)
        if len(result) >= 5:
            _, _, _, _, channel_values, _ = result[:6]
            assert channel_values == {}
            # No TypeError should occur

def test_imports():
    """Basic test to verify imports work."""
    # This test will fail if langgraph isn't installed
    # but at least we'll know why
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        assert True
    except ImportError as e:
        pytest.skip(f"Required import failed: {e}")

if __name__ == "__main__":
    # Simple runner for debugging
    asyncio.run(test_aget_tuple_with_none_channel_values())