import pytest

from strands.models import Model as SAModel


class DummyModel(SAModel):
    def update_config(self, **model_config):
        return model_config

    def get_config(self):
        return {}

    async def structured_output(self, output_model, prompt=None, system_prompt=None, **kwargs):
        yield {"output": output_model(name="dummy", age=0)}

    async def stream(self, messages, tool_specs=None, system_prompt=None):
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockDelta": {"delta": {"text": "dummy response"}}}
        yield {"messageStop": {"stopReason": "end_turn"}}


@pytest.mark.asyncio
async def test_estimate_tokens_method_exists_and_returns_int():
    model = DummyModel()
    messages = [
        {"role": "user", "content": [{"text": "Hello world"}]},
        {"role": "assistant", "content": [{"text": "Hi there"}]},
    ]
    # Call estimate_tokens with only messages
    count = await model.count_tokens(messages=messages)
    assert isinstance(count, int)
    assert count > 0

    # Call estimate_tokens with system_prompt
    count2 = await model.count_tokens(messages=messages, system_prompt="System prompt here")
    assert isinstance(count2, int)
    assert count2 >= count

    # Call estimate_tokens with tool_specs
    tool_specs = [
        {
            "name": "tool1",
            "description": "A test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
    ]
    count3 = await model.count_tokens(messages=messages, tool_specs=tool_specs)
    assert isinstance(count3, int)
    assert count3 >= count

    # Call estimate_tokens with system_prompt_content
    system_prompt_content = [{"text": "System prompt content"}]
    count4 = await model.count_tokens(messages=messages, system_prompt_content=system_prompt_content)
    assert isinstance(count4, int)
    assert count4 >= count

    # system_prompt_content takes priority over system_prompt
    count5 = await model.count_tokens(
        messages=messages,
        system_prompt="Long system prompt",
        system_prompt_content=system_prompt_content,
    )
    assert count5 == count4


@pytest.mark.asyncio
async def test_estimate_tokens_counts_text_and_tool_use_blocks():
    model = DummyModel()
    messages = [
        {
            "role": "assistant",
            "content": [
                {"text": "Some text"},
                {
                    "toolUse": {
                        "toolUseId": "abc",
                        "name": "my_tool",
                        "input": {"query": "test query"},
                    }
                },
            ],
        }
    ]
    count = await model.count_tokens(messages=messages)
    # Should count tokens for "Some text" and toolUse name and input
    assert count > 0


@pytest.mark.asyncio
async def test_estimate_tokens_counts_tool_result_and_reasoning_blocks():
    model = DummyModel()
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "abc",
                        "content": [{"text": "tool result output"}],
                        "status": "success",
                    }
                },
                {
                    "reasoningContent": {
                        "reasoningText": {"text": "Reasoning text here."}
                    }
                },
            ],
        }
    ]
    count = await model.count_tokens(messages=messages)
    assert count > 0


@pytest.mark.asyncio
async def test_estimate_tokens_skips_binary_content():
    model = DummyModel()
    messages = [
        {
            "role": "user",
            "content": [{"image": {"format": "png", "source": {"bytes": b"fake data"}}}],
        }
    ]
    count = await model.count_tokens(messages=messages)
    # No text content, so count should be zero
    assert count == 0


@pytest.mark.asyncio
async def test_estimate_tokens_counts_guard_and_citations_content():
    model = DummyModel()
    messages = [
        {
            "role": "assistant",
            "content": [
                {"guardContent": {"text": {"text": "Guard content text"}}},
                {
                    "citationsContent": {
                        "content": [{"text": "Citation text"}],
                        "citations": [],
                    }
                },
            ],
        }
    ]
    count = await model.count_tokens(messages=messages)
    assert count > 0


@pytest.mark.asyncio
async def test_estimate_tokens_handles_non_serializable_tool_input():
    model = DummyModel()
    messages = [
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "abc",
                        "name": "my_tool",
                        "input": {"data": b"binary data"},
                    }
                }
            ],
        }
    ]
    count = await model.count_tokens(messages=messages)
    # Should count tool name tokens even if input is not JSON serializable
    assert count >= 1


@pytest.mark.asyncio
async def test_estimate_tokens_handles_non_serializable_tool_spec():
    model = DummyModel()
    messages = [
        {"role": "user", "content": [{"text": "hello"}]},
    ]
    tool_specs = [
        {
            "name": "tool",
            "description": "desc",
            "inputSchema": {"json": {"default": b"bytes"}},
        }
    ]
    count = await model.count_tokens(messages=messages, tool_specs=tool_specs)
    # Should count message tokens at least
    assert count >= 1


@pytest.mark.asyncio
async def test_estimate_tokens_with_empty_inputs_returns_zero():
    model = DummyModel()
    count = await model.count_tokens(messages=[])
    assert count == 0
    count2 = await model.count_tokens(messages=[], tool_specs=[])
    assert count2 == 0
    count3 = await model.count_tokens(messages=[], system_prompt=None)
    assert count3 == 0
    count4 = await model.count_tokens(messages=[], system_prompt_content=[])
    assert count4 == 0
