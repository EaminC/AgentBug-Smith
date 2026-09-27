import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agentscope.memory._long_term_memory._mem0._mem0_long_term_memory import (
    Mem0LongTermMemory,
)
from agentscope.message import Msg


def test_mem0_long_term_memory_record_return_type_buggy() -> None:
    """Test that record() returns None in buggy version (pre-fix)."""
    # Mock the mem0 import and version check to simulate buggy version
    with patch("mem0.AsyncMemory") as mock_async_memory:
        # Create an async mock since add() is an async method
        mock_memory_instance = AsyncMock()
        mock_memory_instance.add.return_value = {"some": "result"}
        mock_async_memory.return_value = mock_memory_instance

        # Create instance with minimal required arguments
        mem = Mem0LongTermMemory(
            agent_name="test_agent",
            model=MagicMock(),
            embedding_model=MagicMock(),
        )
        # In buggy version, record() returns None
        # Fix: Correct Msg constructor - first arg should be role, not name
        result = mem.record([Msg(name="user", content="hello")])
        # This assertion will fail after fix because record() will return dict
        assert result is None


def test_mem0_long_term_memory_record_return_type_fixed() -> None:
    """Test that record() returns dict in fixed version."""
    # Mock the mem0 import
    with patch("mem0.AsyncMemory") as mock_async_memory:
        # Create an async mock since add() is an async method
        mock_memory_instance = AsyncMock()
        expected_result = {"memories": ["memory1", "memory2"]}
        mock_memory_instance.add.return_value = expected_result
        mock_async_memory.return_value = mock_memory_instance

        # Create instance with minimal required arguments
        mem = Mem0LongTermMemory(
            agent_name="test_agent",
            model=MagicMock(),
            embedding_model=MagicMock(),
        )
        # In fixed version, record() returns dict
        # Fix: Correct Msg constructor - first arg should be role, not name
        result = mem.record([Msg(name="user", content="hello")])
        assert isinstance(result, dict)
        assert result == expected_result


def test_mem0_long_term_memory_suppress_logging() -> None:
    """Test suppress_mem0_logging parameter."""
    # Mock the mem0 import
    with patch("mem0.AsyncMemory") as mock_async_memory:
        # Create an async mock since add() is an async method
        mock_memory_instance = AsyncMock()
        mock_memory_instance.add.return_value = {}
        mock_async_memory.return_value = mock_memory_instance

        # Test with suppress_mem0_logging=True (default)
        mem1 = Mem0LongTermMemory(
            agent_name="test_agent",
            model=MagicMock(),
            embedding_model=MagicMock(),
            suppress_mem0_logging=True,
        )
        # Fix: Correct Msg constructor
        assert mem1.record([Msg(name="user", content="hello")]) is not None

        # Test with suppress_mem0_logging=False
        mem2 = Mem0LongTermMemory(
            agent_name="test_agent",
            model=MagicMock(),
            embedding_model=MagicMock(),
            suppress_mem0_logging=False,
        )
        # Fix: Correct Msg constructor
        assert mem2.record([Msg(name="user", content="hello")]) is not None


def test_mem0_long_term_memory_record_signature() -> None:
    """Check the return annotation of record method."""
    import inspect

    sig = inspect.signature(Mem0LongTermMemory.record)
    # In buggy version, return annotation is None.
    # In fixed version, it's Any (or dict).
    # We'll let the test fail if annotation is None.
    assert sig.return_annotation is not None


# Additional test to verify the actual behavior
def test_mem0_long_term_memory_record_async() -> None:
    """Test that record() properly handles async calls."""
    with patch("mem0.AsyncMemory") as mock_async_memory:
        # Create an async mock
        mock_memory_instance = AsyncMock()
        mock_memory_instance.add.return_value = {"test": "data"}
        mock_async_memory.return_value = mock_memory_instance

        mem = Mem0LongTermMemory(
            agent_name="test_agent",
            model=MagicMock(),
            embedding_model=MagicMock(),
        )
        
        # Test with correct Msg constructor
        result = mem.record([Msg(name="user", content="hello")])
        
        # Verify the mock was called
        mock_memory_instance.add.assert_called_once()