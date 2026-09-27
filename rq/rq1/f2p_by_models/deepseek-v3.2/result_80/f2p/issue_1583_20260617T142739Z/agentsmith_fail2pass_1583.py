import pytest
from unittest.mock import Mock, patch, MagicMock
from aider.models import ModelSettings
from aider.sendchat import send_completion, simple_send_with_retries


def test_extra_body_in_model_settings():
    """Test that ModelSettings supports extra_body field."""
    extra_body_config = {
        "provider": {
            "order": ["OpenAI", "Together"]
        }
    }
    
    model = ModelSettings(
        name="openrouter/google/gemma-2-9b-it:free",
        extra_body=extra_body_config
    )
    
    assert model.extra_body == extra_body_config


def test_send_completion_with_extra_body():
    """Test that send_completion passes extra_body to litellm."""
    extra_body_config = {
        "provider": {
            "order": ["OpenAI", "Together"]
        }
    }
    
    messages = [{"role": "user", "content": "Hello"}]
    
    # Mock the litellm.completion call
    with patch('aider.sendchat.litellm.completion') as mock_completion:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Call send_completion with extra_body
        hash_val, response = send_completion(
            model_name="openrouter/google/gemma-2-9b-it:free",
            messages=messages,
            functions=None,
            stream=False,
            temperature=0,
            extra_body=extra_body_config
        )
        
        # Verify that litellm.completion was called with extra_body
        assert mock_completion.called
        call_kwargs = mock_completion.call_args[1]
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"] == extra_body_config


def test_send_completion_without_extra_body():
    """Test that send_completion works without extra_body (backward compatibility)."""
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('aider.sendchat.litellm.completion') as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Call send_completion without extra_body
        hash_val, response = send_completion(
            model_name="gpt-4",
            messages=messages,
            functions=None,
            stream=False,
            temperature=0
        )
        
        # Verify the call succeeded
        assert mock_completion.called
        call_kwargs = mock_completion.call_args[1]
        # extra_body should not be in kwargs if not provided
        assert "extra_body" not in call_kwargs


def test_simple_send_with_retries_with_extra_body():
    """Test that simple_send_with_retries passes extra_body."""
    extra_body_config = {
        "provider": {
            "order": ["OpenAI"]
        }
    }
    
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('aider.sendchat.litellm.completion') as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Call simple_send_with_retries with extra_body
        response = simple_send_with_retries(
            model_name="openrouter/google/gemma-2-9b-it:free",
            messages=messages,
            extra_body=extra_body_config
        )
        
        # Verify that litellm.completion was called with extra_body
        assert mock_completion.called
        call_kwargs = mock_completion.call_args[1]
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"] == extra_body_config
        assert response == "Test response"


def test_simple_send_with_retries_without_extra_body():
    """Test that simple_send_with_retries works without extra_body."""
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('aider.sendchat.litellm.completion') as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Call simple_send_with_retries without extra_body
        response = simple_send_with_retries(
            model_name="gpt-4",
            messages=messages
        )
        
        # Verify the call succeeded
        assert mock_completion.called
        call_kwargs = mock_completion.call_args[1]
        assert "extra_body" not in call_kwargs
        assert response == "Test response"


def test_send_completion_with_extra_body_and_extra_headers():
    """Test that send_completion handles both extra_body and extra_headers."""
    extra_body_config = {
        "provider": {
            "order": ["OpenAI", "Together"]
        }
    }
    extra_headers = {
        "HTTP-Referer": "https://example.com"
    }
    
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('aider.sendchat.litellm.completion') as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Call send_completion with both extra_body and extra_headers
        hash_val, response = send_completion(
            model_name="openrouter/google/gemma-2-9b-it:free",
            messages=messages,
            functions=None,
            stream=False,
            temperature=0,
            extra_headers=extra_headers,
            extra_body=extra_body_config
        )
        
        # Verify both are passed
        assert mock_completion.called
        call_kwargs = mock_completion.call_args[1]
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"] == extra_body_config
        assert "extra_headers" in call_kwargs
        assert call_kwargs["extra_headers"] == extra_headers
