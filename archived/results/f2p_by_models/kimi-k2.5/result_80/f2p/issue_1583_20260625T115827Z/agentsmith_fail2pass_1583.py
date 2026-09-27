import pytest
from aider.models import ModelSettings
from aider.sendchat import send_completion


def test_model_settings_extra_body_field():
    """Test that ModelSettings accepts extra_body field."""
    extra_body = {"provider": {"order": ["OpenAI", "Together"]}}
    
    # This should work after the patch, fail before with:
    # TypeError: ModelSettings.__init__() got an unexpected keyword argument 'extra_body'
    settings = ModelSettings(
        name="openrouter/test-model",
        extra_body=extra_body
    )
    
    assert hasattr(settings, 'extra_body')
    assert settings.extra_body == extra_body


def test_send_completion_accepts_extra_body(monkeypatch):
    """Test that send_completion accepts and passes extra_body to litellm."""
    from aider import llm
    
    call_args = {}
    
    def fake_completion(**kwargs):
        call_args.update(kwargs)
        class FakeMessage:
            content = "test"
            tool_calls = None
        class FakeChoice:
            message = FakeMessage()
        class FakeResponse:
            choices = [FakeChoice()]
        return FakeResponse()
    
    monkeypatch.setattr(llm.litellm, 'completion', fake_completion)
    
    extra_body = {"provider": {"order": ["OpenAI"]}}
    
    # This should work after the patch, fail before with:
    # TypeError: send_completion() got an unexpected keyword argument 'extra_body'
    send_completion(
        model_name="openrouter/test-model",
        messages=[{"role": "user", "content": "hello"}],
        functions=None,
        stream=False,
        temperature=0.5,
        extra_body=extra_body
    )
    
    # Verify extra_body was passed to litellm.completion
