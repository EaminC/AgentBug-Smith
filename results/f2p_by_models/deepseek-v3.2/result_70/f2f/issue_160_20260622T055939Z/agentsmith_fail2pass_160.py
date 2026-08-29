import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import what's actually available based on the error message
# The error said: "Did you mean: 'model'?" from mle.agents.coder
# So let's check what's actually in that module
try:
    from mle.agents.coder import model as coder_model
    HAS_CODER_MODEL = True
except ImportError:
    HAS_CODER_MODEL = False

# Always try to import Model from mle.model
from mle.model import Model


class TestCoderAgentBug160:
    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_claude_model_handles_tool_calls(self):
        """Test that Claude model properly handles tool_use responses.
        
        This tests the core bug: when Claude returns a tool_use response,
        the model should process it and call the appropriate function.
        """
        with patch('mle.model.OpenAI') as mock_openai_class, \
             patch('mle.model.Anthropic') as mock_anthropic_class:
            
            # Mock the Anthropic client
            mock_anthropic = MagicMock()
            mock_anthropic_class.return_value = mock_anthropic
            
            # Mock the messages.create method
            mock_messages = MagicMock()
            mock_anthropic.messages = mock_messages
            
            # Create a mock tool_use response
            mock_tool_use = MagicMock()
            mock_tool_use.type = "tool_use"
            mock_tool_use.name = "test_function"
            mock_tool_use.id = "tool_123"
            mock_tool_use.input = {"param": "value"}
            
            mock_completion = MagicMock()
            mock_completion.content = [mock_tool_use]
            mock_completion.stop_reason = "tool_use"
            
            mock_messages.create.return_value = mock_completion
            
            # Create model instance
            model = Model(api_key="test-key", model="claude-3-opus-20240229")
            
            # Test query with functions
            chat_history = [
                {"role": "user", "content": "Test tool call"}
            ]
            
            functions = [
                {
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param": {"type": "string"}
                        }
                    }
                }
            ]
            
            # This should trigger tool_use handling
            # We need to mock the recursive call that happens after tool execution
            with patch.object(model, '_handle_tool_use') as mock_handle_tool_use:
                mock_handle_tool_use.return_value = "Tool executed successfully"
                
                response = model.query(chat_history, functions=functions)
                
                # Check that _handle_tool_use was called
                mock_handle_tool_use.assert_called_once()
                
                # The response should be from the handler
                assert response == "Tool executed successfully"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_claude_model_handles_response_format(self):
        """Test that Claude model properly handles response_format parameter."""
        with patch('mle.model.OpenAI') as mock_openai_class, \
             patch('mle.model.Anthropic') as mock_anthropic_class:
            
            mock_anthropic = MagicMock()
            mock_anthropic_class.return_value = mock_anthropic
            
            mock_messages = MagicMock()
            mock_anthropic.messages = mock_messages
            
            mock_completion = MagicMock()
            mock_completion.content = [MagicMock()]
            mock_completion.content[0].text = '{"status": "success"}'
            mock_completion.stop_reason = "end_turn"
            mock_messages.create.return_value = mock_completion
            
            model = Model(api_key="test-key", model="claude-3-opus-20240229")
            
            chat_history = [{"role": "user", "content": "Give me JSON"}]
            
            # Test with response_format
            response = model.query(
                chat_history, 
                response_format={"type": "json_object"}
            )
            
            # Check that response_format was processed
            call_kwargs = mock_messages.create.call_args[1]
            system_prompt = call_kwargs.get('system', '')
            
            # The system prompt should contain JSON instructions
            # This tests the bug fix for response_format handling
            assert "json" in system_prompt.lower() or "json_object" in system_prompt

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_model_initialization(self):
        """Test basic model initialization and query."""
        with patch('mle.model.OpenAI') as mock_openai_class, \
             patch('mle.model.Anthropic') as mock_anthropic_class:
            
            mock_anthropic = MagicMock()
            mock_anthropic_class.return_value = mock_anthropic
            
            mock_messages = MagicMock()
            mock_anthropic.messages = mock_messages
            
            mock_completion = MagicMock()
            mock_completion.content = [MagicMock()]
            mock_completion.content[0].text = "Test response"
            mock_completion.stop_reason = "end_turn"
            mock_messages.create.return_value = mock_completion
            
            model = Model(api_key="test-key", model="claude-3-opus-20240229")
            
            # Test basic query
            chat_history = [{"role": "user", "content": "Hello"}]
            response = model.query(chat_history)
            
            assert response == "Test response"
            mock_messages.create.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])