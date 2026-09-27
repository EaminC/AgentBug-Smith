import os
import sys
import asyncio
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Add the examples directory to the path
examples_dir = Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(examples_dir))

# Try to import from the correct location
try:
    # Import the DeepResearchAgent from the examples
    from agent.deep_research_agent.deep_research_agent import DeepResearchAgent
except ImportError as e:
    # If that fails, try alternative import paths
    print(f"Import error: {e}")
    # Try to find the module by exploring the directory structure
    import agentscope
    # Check if DeepResearchAgent is available in agentscope
    if hasattr(agentscope, 'DeepResearchAgent'):
        from agentscope import DeepResearchAgent
    else:
        # Last resort: try to import from the current directory structure
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            from examples.agent.deep_research_agent.deep_research_agent import DeepResearchAgent
        except ImportError:
            raise

import pytest


def test_deep_research_agent_extract_text_from_blocks():
    """Test that _extract_text_from_blocks correctly extracts text from blocks with thinking block first."""
    # Create a minimal agent instance without real model initialization
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock the model to avoid real API calls
        mock_model = MagicMock()
        mock_model.stream = False
        mock_model.name = "test-model"
        mock_model.call = AsyncMock()
        mock_model.call.return_value = {"raw": None}

        # Mock the toolkit to avoid tool registration issues
        mock_toolkit = MagicMock()
        mock_toolkit.register_tool_function = MagicMock()

        # Create agent with minimal required arguments
        agent = DeepResearchAgent(
            name="test_agent",
            model=mock_model,
            user_query="test query",
            output_dir=tmpdir,
        )

        # Replace the toolkit with mock to avoid side effects
        agent.toolkit = mock_toolkit

        # Test case 1: blocks with thinking block first (buggy case)
        blocks_with_thinking = [
            {"type": "thinking", "thinking": "I need to think about this..."},
            {"type": "text", "text": "This is the actual text content."}
        ]
        result = agent._extract_text_from_blocks(blocks_with_thinking)
        assert result == "This is the actual text content.", f"Expected 'This is the actual text content.', got {result}"

        # Test case 2: blocks with text block first (original case)
        blocks_text_first = [
            {"type": "text", "text": "Direct text content."}
        ]
        result = agent._extract_text_from_blocks(blocks_text_first)
        assert result == "Direct text content.", f"Expected 'Direct text content.', got {result}"

        # Test case 3: multiple blocks, text not first
        blocks_multiple = [
            {"type": "thinking", "thinking": "First thought"},
            {"type": "thinking", "thinking": "Second thought"},
            {"type": "text", "text": "Final answer"}
        ]
        result = agent._extract_text_from_blocks(blocks_multiple)
        assert result == "Final answer.", f"Expected 'Final answer.', got {result}"

        # Test case 4: no text block - should raise ValueError
        blocks_no_text = [
            {"type": "thinking", "thinking": "Only thinking"},
            {"type": "thinking", "thinking": "More thinking"}
        ]
        try:
            agent._extract_text_from_blocks(blocks_no_text)
            assert False, "Expected ValueError for blocks without text"
        except ValueError as e:
            assert "No text block found" in str(e), f"Expected 'No text block found' error, got {e}"

        # Test case 5: empty blocks list
        blocks_empty = []
        try:
            agent._extract_text_from_blocks(blocks_empty)
            assert False, "Expected ValueError for empty blocks"
        except ValueError as e:
            assert "No text block found" in str(e), f"Expected 'No text block found' error, got {e}"

        # Test case 6: blocks with missing type key
        blocks_missing_type = [
            {"text": "Some text"}
        ]
        try:
            agent._extract_text_from_blocks(blocks_missing_type)
            assert False, "Expected ValueError for blocks missing type"
        except ValueError as e:
            assert "No text block found" in str(e), f"Expected 'No text block found' error, got {e}"


def test_deep_research_agent_generate_response_with_thinking_blocks():
    """Test that generate_response handles thinking blocks correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock model that returns thinking blocks
        mock_model = MagicMock()
        mock_model.stream = False
        mock_model.name = "Qwen3.5-397B-A17B-FPB"
        mock_model.call = AsyncMock()
        
        # Mock the toolkit
        mock_toolkit = MagicMock()
        mock_toolkit.register_tool_function = MagicMock()

        # Create agent
        agent = DeepResearchAgent(
            name="test_agent",
            model=mock_model,
            user_query="test query",
            output_dir=tmpdir,
        )
        agent.toolkit = mock_toolkit

        # Test that the method exists and is callable
        assert hasattr(agent, '_extract_text_from_blocks'), "Agent should have _extract_text_from_blocks method"
        assert callable(agent._extract_text_from_blocks), "_extract_text_from_blocks should be callable"

        # Test with the actual bug scenario: simulate what happens in _generate_deepresearch_report
        mock_blocks = [
            {"type": "thinking", "thinking": "I'm thinking about the report..."},
            {"type": "text", "text": "This is the final report content."}
        ]
        
        # Test that the extraction works on these blocks
        extracted = agent._extract_text_from_blocks(mock_blocks)
        assert extracted == "This is the final report content.", \
            f"Should extract text from thinking blocks, got {extracted}"


def test_deep_research_agent_initialization():
    """Test that agent initializes correctly with mocked dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_model = MagicMock()
        mock_model.stream = False
        mock_model.name = "test-model"
        
        # Mock toolkit
        mock_toolkit = MagicMock()
        mock_toolkit.register_tool_function = MagicMock()

        # Create agent - should not crash
        agent = DeepResearchAgent(
            name="test_agent",
            model=mock_model,
            user_query="test query",
            output_dir=tmpdir,
        )
        
        # Verify agent has required attributes
        assert agent.name == "test_agent"
        assert agent.model == mock_model
        assert agent.user_query == "test query"
        
        # The _extract_text_from_blocks method should exist after fix
        assert hasattr(agent, '_extract_text_from_blocks'), \
            "Agent should have _extract_text_from_blocks method after fix"


@pytest.mark.asyncio
async def test_async_extraction():
    """Async test to verify the extraction works in async context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_model = MagicMock()
        mock_model.stream = False
        mock_model.name = "test-model"
        mock_model.call = AsyncMock()
        
        mock_toolkit = MagicMock()
        mock_toolkit.register_tool_function = MagicMock()

        agent = DeepResearchAgent(
            name="test_agent",
            model=mock_model,
            user_query="test query",
            output_dir=tmpdir,
        )
        agent.toolkit = mock_toolkit

        # Test extraction directly
        blocks = [
            {"type": "thinking", "thinking": "Thinking..."},
            {"type": "text", "text": "Async text result"}
        ]
        
        result = agent._extract_text_from_blocks(blocks)
        assert result == "Async text result"


# Run tests with pytest if executed directly
if __name__ == "__main__":
    # Run synchronous tests
    test_deep_research_agent_extract_text_from_blocks()
    test_deep_research_agent_generate_response_with_thinking_blocks()
    test_deep_research_agent_initialization()
    
    # Run async test
    asyncio.run(test_async_extraction())
    
    print("All tests passed!")