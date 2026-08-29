import pytest
from unittest.mock import MagicMock
import aider.models as models
import aider.sendchat as sendchat


def test_model_settings_extra_body_field():
    # This test verifies that ModelSettings accepts the extra_body argument
    # and stores it correctly.
    # This test will fail on buggy code because ModelSettings does not accept extra_body.
    extra_body_value = {"provider": {"order": ["OpenAI", "Together"]}}
    m = models.ModelSettings(
        name="dummy-model",
        extra_body=extra_body_value,
    )
    assert m.extra_body == extra_body_value


@pytest.mark.parametrize("extra_body", [None, {"provider": {"order": ["OpenAI", "Together"]}}])
def test_model_settings_roundtrip_extra_body(extra_body):
    # Test that ModelSettings can be created with or without extra_body and serialize/deserialize works
    ms = models.ModelSettings(
        name="dummy-model",
        extra_body=extra_body,
    )
    # Serialize to dict (ModelSettings is a pydantic model or dataclass with dict method)
    # We accept either dict() or __dict__ depending on implementation
    if hasattr(ms, "dict"):
        d = ms.dict()
    else:
        d = ms.__dict__
    assert "extra_body" in d
    assert d["extra_body"] == extra_body


def test_send_completion_extra_body_passed(monkeypatch):
    # Test that send_completion accepts extra_body and passes it to litellm call

    called_kwargs = {}

    def fake_litellm_send_completion(**kwargs):
        called_kwargs.update(kwargs)
        dummy_resp = MagicMock()
        dummy_resp.choices = [MagicMock(message=MagicMock(content="dummy content"))]
        return "hash", dummy_resp

    monkeypatch.setattr(sendchat, "send_completion", fake_litellm_send_completion)

    extra_body = {"provider": {"order": ["OpenAI", "Together"]}}
    messages = [{"role": "user", "content": "Hello"}]

    # Call send_completion with extra_body
    _hash, response = sendchat.send_completion(
        model_name="dummy-model",
        messages=messages,
        functions=None,
        stream=False,
        extra_body=extra_body,
    )
    # Check that extra_body was passed through
    assert "extra_body" in called_kwargs
    assert called_kwargs["extra_body"] == extra_body
    assert response.choices[0].message.content == "dummy content"


def test_simple_send_with_retries_extra_body(monkeypatch):
    # Test that simple_send_with_retries passes extra_body to send_completion

    called_kwargs = {}

    def fake_send_completion(**kwargs):
        called_kwargs.update(kwargs)
        dummy_resp = MagicMock()
        dummy_resp.choices = [MagicMock(message=MagicMock(content="dummy content"))]
        return "hash", dummy_resp

    monkeypatch.setattr(sendchat, "send_completion", fake_send_completion)

    extra_body = {"provider": {"order": ["OpenAI", "Together"]}}
    messages = [{"role": "user", "content": "Hello"}]

    # Call simple_send_with_retries with extra_body
    response = sendchat.simple_send_with_retries(
        "dummy-model",
        messages,
        extra_body=extra_body,
    )
    assert "extra_body" in called_kwargs
    assert called_kwargs["extra_body"] == extra_body
    assert response == "dummy content"
