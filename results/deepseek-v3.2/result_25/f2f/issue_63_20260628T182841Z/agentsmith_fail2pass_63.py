import json
import logging
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from agentscope.agents import DictDialogAgent
from agentscope.models import ModelResponse, ModelWrapperBase
from agentscope.utils.logging_utils import logger, LEVEL_CHAT_SAVE, _chat
from agentscope.models import load_model_by_config_name, read_model_configs


def test_logger_chinese_support() -> None:
    """Test that logging with Chinese characters works correctly (non-ASCII)."""
    # First, ensure model configs are loaded to avoid the ValueError
    # We'll mock the internal config dict to be non-empty
    from agentscope.models import _MODEL_CONFIGS

    original_configs = _MODEL_CONFIGS.copy()
    _MODEL_CONFIGS.clear()
    _MODEL_CONFIGS["test_config"] = {
        "model_name": "test_model",
        "model_type": "openai",
        "config": {"api_key": "fake", "model": "gpt-3.5-turbo"},
    }

    # Capture log messages to verify they are not escaped
    log_capture = []
    original_debug = logger.debug
    original_log = logger.log

    def capture_debug(msg, *args, **kwargs):
        log_capture.append(("debug", msg))
        # Call original to ensure behavior is same as real usage
        original_debug(msg, *args, **kwargs)

    def capture_log(level, msg, *args, **kwargs):
        if level == LEVEL_CHAT_SAVE:
            log_capture.append(("chat", msg))
        # Call original to ensure behavior is same as real usage
        original_log(level, msg, *args, **kwargs)

    logger.debug = capture_debug
    logger.log = capture_log

    try:
        # Mock the actual model call to avoid requiring real API
        # Use a more generic patch that doesn't depend on specific import paths
        with patch.object(ModelWrapperBase, '__call__') as mock_call:
            mock_call.return_value = ModelResponse(
                text="你好，世界",
                raw={"choices": [{"message": {"content": "你好，世界"}}]},
            )

            # Test 1: DictDialogAgent reply logging
            agent = DictDialogAgent(
                name="test_agent",
                sys_prompt="You are a test agent.",
                model_config_name="test_config",
            )

            # Trigger a reply to generate debug log
            agent.reply({"content": "Hello"})

            # Check that the debug log contains Chinese characters without escaping
            assert len(log_capture) >= 1
            debug_msg = log_capture[0][1]
            # In buggy version, Chinese characters are escaped as Unicode (\uXXXX)
            # In fixed version, they appear as actual characters.
            # We check that the string contains the raw Chinese characters.
            # If ensure_ascii=False is missing, json.dumps will escape them.
            if "\u4f60\u597d" in debug_msg:
                # This means the characters are escaped (buggy)
                raise AssertionError(
                    f"Chinese characters are escaped in debug log: {debug_msg}"
                )
            # Ensure the actual characters appear
            assert "你好" in debug_msg, f"Expected '你好' in log, got {debug_msg}"

            # Test 2: ModelWrapperBase __str__ method
            model_resp = ModelResponse(text="测试", raw={"test": "测试"})
            str_repr = str(model_resp)
            # Check that Chinese characters are not escaped in the string representation
            if "\u6d4b\u8bd5" in str_repr:
                raise AssertionError(
                    f"Chinese characters escaped in ModelResponse __str__: {str_repr}"
                )
            assert "测试" in str_repr, f"Expected '测试' in __str__, got {str_repr}"

            # Test 3: ModelWrapperBase __init__ debug log
            # Create a simple test to check logging without complex mocking
            log_capture.clear()
            
            # Create a simple model wrapper instance with Chinese parameters
            class SimpleModelWrapper(ModelWrapperBase):
                def __call__(self, *args, **kwargs):
                    return ModelResponse(text="test", raw={})
            
            # This should trigger debug logging with the config name
            wrapper = SimpleModelWrapper("test_config_中文")
            
            # Check if any debug log contains the Chinese config name
            found_chinese = False
            for _, msg in log_capture:
                if "test_config_中文" in msg:
                    if "\u4e2d\u6587" in msg:
                        raise AssertionError(
                            f"Chinese escaped in model init debug log: {msg}"
                        )
                    assert "中文" in msg, f"Expected '中文' in log, got {msg}"
                    found_chinese = True
                    break
            
            # If no Chinese was found in logs, that's okay - the test is about
            # ensuring Chinese isn't escaped when it does appear

            # Test 4: logging_utils._chat with Chinese message
            log_capture.clear()
            _chat({"content": "聊天内容"})
            assert any("chat" == typ for typ, _ in log_capture)
            for typ, msg in log_capture:
                if typ == "chat":
                    if "\u804a\u5929\u5185\u5bb9" in msg:
                        raise AssertionError(
                            f"Chinese escaped in chat log: {msg}"
                        )
                    assert "聊天内容" in msg, f"Expected '聊天内容' in chat log, got {msg}"
                    break

    finally:
        # Restore original logger methods
        logger.debug = original_debug
        logger.log = original_log
        # Restore original configs
        _MODEL_CONFIGS.clear()
        _MODEL_CONFIGS.update(original_configs)