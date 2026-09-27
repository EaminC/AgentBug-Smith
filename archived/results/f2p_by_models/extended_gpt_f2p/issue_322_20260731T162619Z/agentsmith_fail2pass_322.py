import builtins
import types
import pytest

import gpt_engineer.ai as ai


class DummyTokenizer:
    def __init__(self):
        self.encode_calls = []

    def encode(self, txt):
        self.encode_calls.append(txt)
        # Simple token count: number of words
        return txt.split()


class DummyOpenAIChatCompletion:
    def __init__(self):
        self.create_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        # Return dummy streamed chunks
        class DummyStream:
            def __iter__(self_inner):
                # Simulate a single chunk with content "response"
                yield {"choices": [{"delta": {"content": "response"}}]}
        return DummyStream()


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    # Patch openai.ChatCompletion.create to dummy streaming
    dummy_chat_completion = DummyOpenAIChatCompletion()
    monkeypatch.setattr(ai.openai.ChatCompletion, "create", dummy_chat_completion.create)
    yield


@pytest.fixture(autouse=True)
def patch_tiktoken(monkeypatch):
    dummy_tokenizer = DummyTokenizer()
    monkeypatch.setattr(ai.tiktoken, "encoding_for_model", lambda model: dummy_tokenizer)
    monkeypatch.setattr(ai.tiktoken, "get_encoding", lambda name: dummy_tokenizer)
    yield


def test_token_usage_logging_and_formatting():
    # Create AI instance with a dummy model name that triggers fallback tokenizer
    model_name = "nonexistent-model-for-testing"
    ai_instance = ai.AI(model=model_name)

    # Start a conversation with step_name
    system_prompt = "System prompt for testing."
    user_prompt = "User prompt for testing."
    step_name_1 = "start_step"
    messages = ai_instance.start(system_prompt, user_prompt, step_name=step_name_1)

    # The token usage log should have one entry
    assert len(ai_instance.token_usage_log) == 1
    log_entry = ai_instance.token_usage_log[0]
    assert log_entry.step_name == step_name_1
    # The in_step_total_tokens should be sum of prompt and completion tokens
    assert log_entry.in_step_total_tokens == log_entry.in_step_prompt_tokens + log_entry.in_step_completion_tokens
    # The cumulative totals should match the first entry
    assert log_entry.total_tokens == log_entry.in_step_total_tokens

    # Call next again with new prompt and step_name
    step_name_2 = "second_step"
    messages = ai_instance.next(messages, prompt="Another prompt", step_name=step_name_2)
    assert len(ai_instance.token_usage_log) == 2
    second_log = ai_instance.token_usage_log[1]
    assert second_log.step_name == step_name_2
    # Cumulative totals should be increasing
    assert second_log.total_tokens > log_entry.total_tokens

    # The formatted log string should contain headers and entries
    formatted = ai_instance.format_token_usage_log()
    assert "step_name" in formatted
    assert step_name_1 in formatted
    assert step_name_2 in formatted
    # Should have two lines after header
    lines = formatted.strip().splitlines()
    assert len(lines) == 3


def test_token_usage_log_accumulates_correctly():
    ai_instance = ai.AI(model="gpt-4")
    # Prepare dummy messages and answers
    base_messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User prompt"},
    ]
    steps = [
        ("step1", "Hello world!"),
        ("step2", "Another answer."),
        ("step3", "Final answer."),
    ]
    cumulative_prompt = 0
    cumulative_completion = 0
    cumulative_total = 0
    for step_name, answer in steps:
        # Use the real update_token_usage_log method
        ai_instance.update_token_usage_log(base_messages, answer, step_name)
        last_log = ai_instance.token_usage_log[-1]
        # Check step name matches
        assert last_log.step_name == step_name
        # Check totals are sums of parts
        assert last_log.in_step_total_tokens == last_log.in_step_prompt_tokens + last_log.in_step_completion_tokens
        # Check cumulative sums increase
        assert last_log.total_prompt_tokens >= cumulative_prompt
        assert last_log.total_completion_tokens >= cumulative_completion
        assert last_log.total_tokens >= cumulative_total
        cumulative_prompt = last_log.total_prompt_tokens
        cumulative_completion = last_log.total_completion_tokens
        cumulative_total = last_log.total_tokens


def test_start_and_next_methods_token_usage_integration():
    ai_instance = ai.AI(model="gpt-4")
    system_prompt = "System prompt"
    user_prompt = "User prompt"
    step_name_start = "start_step"
    # Start should call next internally and log tokens
    messages = ai_instance.start(system_prompt, user_prompt, step_name=step_name_start)
    assert isinstance(messages, list)
    assert len(ai_instance.token_usage_log) == 1
    assert ai_instance.token_usage_log[0].step_name == step_name_start

    # Next with prompt and step_name should log tokens
    step_name_next = "next_step"
    messages = ai_instance.next(messages, prompt="Follow-up prompt", step_name=step_name_next)
    assert len(ai_instance.token_usage_log) == 2
    assert ai_instance.token_usage_log[-1].step_name == step_name_next


def test_num_tokens_and_num_tokens_from_messages_consistency():
    ai_instance = ai.AI(model="gpt-4")
    text = "Hello world!"
    tokens_count = ai_instance.num_tokens(text)
    # Should be positive integer
    assert isinstance(tokens_count, int)
    assert tokens_count > 0

    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User prompt"},
    ]
    tokens_from_messages = ai_instance.num_tokens_from_messages(messages)
    # Should be positive integer and at least sum of encoded tokens
    assert isinstance(tokens_from_messages, int)
    assert tokens_from_messages >= sum(ai_instance.num_tokens(m["content"]) for m in messages)


def test_format_token_usage_log_output_format():
    ai_instance = ai.AI(model="gpt-4")
    # Add dummy entries manually
    ai_instance.token_usage_log.append(
        ai.TokenUsage(
            step_name="stepA",
            in_step_prompt_tokens=10,
            in_step_completion_tokens=5,
            in_step_total_tokens=15,
            total_prompt_tokens=10,
            total_completion_tokens=5,
            total_tokens=15,
        )
    )
    ai_instance.token_usage_log.append(
        ai.TokenUsage(
            step_name="stepB",
            in_step_prompt_tokens=20,
            in_step_completion_tokens=10,
            in_step_total_tokens=30,
            total_prompt_tokens=30,
            total_completion_tokens=15,
            total_tokens=45,
        )
    )
    formatted = ai_instance.format_token_usage_log()
    lines = formatted.strip().splitlines()
    # Header + 2 entries
    assert len(lines) == 3
    header = lines[0]
    assert header.startswith("step_name,")
    # Check CSV columns count
    assert header.count(",") == 6
    # Check that step names appear in output
    assert "stepA" in formatted
    assert "stepB" in formatted
