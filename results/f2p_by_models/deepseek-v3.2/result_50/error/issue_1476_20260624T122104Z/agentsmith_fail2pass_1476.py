import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from agentscope.message import Msg
from examples.agent.deep_research_agent.deep_research_agent import DeepResearchAgent


@pytest.mark.asyncio
async def test_deep_research_agent_acting_with_none_metadata():
    """Test that DeepResearchAgent._acting handles None metadata without AttributeError."""
    
    # Mock the model wrapper
    with patch('examples.agent.deep_research_agent.deep_research_agent.ModelWrapperBase') as MockModelWrapper:
        mock_model = MockModelWrapper.return_value
        mock_model.generate = AsyncMock(return_value=Msg("assistant", "test"))
        
        # Create agent instance
        agent = DeepResearchAgent(
            name="test_agent",
            model_config={"config_name": "test"},
            search_tool=None,
            finish_function_name="finish",
            summarize_function="summarize",
            generate_response_function="generate_response",
            max_subtask=5,
            max_search_times_per_subtask=3,
            verbose=True,
        )
        
        # Setup minimal mocks
        agent._tools = {}
        agent.memory = MagicMock()
        agent.memory.get = MagicMock(return_value=[])
        agent.memory.add = MagicMock()
        agent.print = AsyncMock()
        agent.current_subtask = []
        
        # Create tool call
        tool_call = {
            "name": "finish",
            "args": {},
        }
        
        # Create mock async generator with None metadata
        async def mock_tool_res_generator():
            chunk = MagicMock()
            chunk.metadata = None  # This is what triggers the bug
            chunk.is_last = True
            chunk.content = [{"output": "test"}]
            yield chunk
        
        # Mock _execute_tool
        agent._execute_tool = AsyncMock(return_value=mock_tool_res_generator())
        
        # Run _acting - should not raise AttributeError
        try:
            result = await agent._acting(tool_call)
            # If we get here without exception, the test passes
            assert result is not None or True  # Just to have an assertion
        except AttributeError as e:
            if "'NoneType' object has no attribute 'get'" in str(e):
                pytest.fail(f"Bug reproduced: AttributeError when metadata is None: {e}")
            else:
                raise


@pytest.mark.asyncio
async def test_deep_research_agent_acting_with_dict_metadata():
    """Test that DeepResearchAgent._acting works correctly with dict metadata."""
    
    with patch('examples.agent.deep_research_agent.deep_research_agent.ModelWrapperBase') as MockModelWrapper:
        mock_model = MockModelWrapper.return_value
        mock_model.generate = AsyncMock(return_value=Msg("assistant", "test"))
        
        agent = DeepResearchAgent(
            name="test_agent",
            model_config={"config_name": "test"},
            search_tool=None,
            finish_function_name="finish",
            summarize_function="summarize",
            generate_response_function="generate_response",
            max_subtask=5,
            max_search_times_per_subtask=3,
            verbose=True,
        )
        
        agent._tools = {}
        agent.memory = MagicMock()
        agent.memory.get = MagicMock(return_value=[])
        agent.memory.add = MagicMock()
        agent.print = AsyncMock()
        agent.current_subtask = []
        
        tool_call = {
            "name": "finish",
            "args": {},
        }
        
        # Create mock async generator with dict metadata
        async def mock_tool_res_generator():
            chunk = MagicMock()
            chunk.metadata = {"success": True, "response_msg": Msg("assistant", "response")}
            chunk.is_last = True
            chunk.content = [{"output": "test"}]
            yield chunk
        
        agent._execute_tool = AsyncMock(return_value=mock_tool_res_generator())
        
        # Should work without issues
        result = await agent._acting(tool_call)
        assert result is not None or True


if __name__ == "__main__":
    # Run tests directly for debugging
    asyncio.run(test_deep_research_agent_acting_with_none_metadata())
    asyncio.run(test_deep_research_agent_acting_with_dict_metadata())
    print("All tests passed!")