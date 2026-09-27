import os
import pytest
import asyncio
import litellm

def test_litellm_version_allows_openai_178():
    # Check that litellm version is at least 1.72.0 (the fixed version)
    version_str = getattr(litellm, "__version__", None)
    assert version_str is not None, "litellm package does not have __version__ attribute"
    parts = version_str.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    assert (major, minor, patch) >= (1, 72, 0), f"litellm version is {version_str}, expected >= 1.72.0"

@pytest.mark.asyncio
async def test_litellm_call_returns_string(monkeypatch):
    # Identify async call method in LiteLLM
    candidate_methods = ["_acall", "_call_async", "_call", "call_async"]
    method_to_patch = None
    for m in candidate_methods:
        if hasattr(litellm.LiteLLM, m):
            method_to_patch = m
            break
    assert method_to_patch is not None, "Could not find internal async call method to patch in litellm.LiteLLM"

    async def dummy_async_call(self, *args, **kwargs):
        return "dummy response"

    monkeypatch.setattr(litellm.LiteLLM, method_to_patch, dummy_async_call)

    llm = litellm.LiteLLM(api_key=os.getenv("OPENAI_API_KEY"))

    if hasattr(llm, "acall"):
        result = await llm.acall("Hello")
    elif hasattr(llm, "call_async"):
        result = await llm.call_async("Hello")
    else:
        result = llm("Hello")

    assert isinstance(result, str), "LiteLLM call did not return a string"

@pytest.mark.asyncio
async def test_litellm_call_works_with_openai_178(monkeypatch):
    candidate_methods = ["_acall", "_call_async", "_call", "call_async"]
    method_to_patch = None
    for m in candidate_methods:
        if hasattr(litellm.LiteLLM, m):
            method_to_patch = m
            break
    assert method_to_patch is not None, "Could not find internal async call method to patch in litellm.LiteLLM"

    async def dummy_openai_call(self, *args, **kwargs):
        return "openai 1.78 compatible response"

    monkeypatch.setattr(litellm.LiteLLM, method_to_patch, dummy_openai_call)

    llm = litellm.LiteLLM(api_key=os.getenv("OPENAI_API_KEY"))

    if hasattr(llm, "acall"):
        result = await llm.acall("Test multi-image input support")
    elif hasattr(llm, "call_async"):
        result = await llm.call_async("Test multi-image input support")
    else:
        result = llm("Test multi-image input support")

    assert result == "openai 1.78 compatible response", "LiteLLM call did not return expected openai 1.78 compatible response"