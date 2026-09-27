from interpreter.terminal_interface.magic_commands import handle_count_tokens
from interpreter.utils.count_tokens import count_messages_tokens, count_tokens, token_cost


class MockInterpreter:
    """Mock interpreter object for testing magic commands"""
    def __init__(self):
        self.system_message = "You are a helpful assistant."
        self.messages = []
        self.model = "gpt-4"


def test_count_tokens_function_exists():
    """Test that count_tokens function exists and works"""
    text = "Hello world"
    tokens = count_tokens(text, model="gpt-4")
    assert isinstance(tokens, int)
    assert tokens > 0


def test_token_cost_function_exists():
    """Test that token_cost function exists and returns valid cost"""
    cost = token_cost(tokens=100, model="gpt-4")
    assert isinstance(cost, (int, float))
    assert cost >= 0


def test_count_messages_tokens_function_exists():
    """Test that count_messages_tokens function exists and works with message lists"""
    messages = [
        {"role": "system", "message": "You are helpful."},
        {"role": "user", "message": "Hello", "code": "print('hi')", "output": "hi"}
    ]
    tokens, cost = count_messages_tokens(messages=messages, model="gpt-4")
    assert isinstance(tokens, int)
    assert tokens > 0
    assert isinstance(cost, (int, float))
    assert cost >= 0


def test_handle_count_tokens_with_empty_messages():
    """Test handle_count_tokens with empty conversation"""
    mock = MockInterpreter()
    # Should not raise any exception
    handle_count_tokens(mock, "")


def test_handle_count_tokens_with_messages():
    """Test handle_count_tokens with messages in conversation"""
    mock = MockInterpreter()
    mock.messages = [
        {"role": "user", "message": "Hello there"},
        {"role": "assistant", "message": "Hi!"}
    ]
    # Should not raise any exception
    handle_count_tokens(mock, "")


def test_handle_count_tokens_integration():
    """Integration test verifying the full token counting flow"""
    mock = MockInterpreter()
    mock.messages = [{"role": "user", "message": "What is 2+2?"}]
    mock.model = "gpt-3.5-turbo"
    
    # Verify this runs without error
    handle_count_tokens(mock, "")
    
    # Verify the underlying function works
    messages = [{"role": "system", "message": mock.system_message}] + mock.messages
    tokens, cost = count_messages_tokens(messages=messages, model=mock.model)
    assert tokens > 0
    assert cost >= 0
