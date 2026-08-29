import json
import logging
import os
import pytest


def test_logging_utils_logger_log_ensure_ascii_false(caplog):
    """
    Test that src.agentscope.utils.logging_utils._chat logs JSON with ensure_ascii=False,
    so Chinese characters appear correctly in logs.
    """
    from src.agentscope.utils import logging_utils

    caplog.set_level(logging.INFO, logger="agentscope")

    message = {"text": "测试中文字符", "nested": {"key": "值"}}
    logging_utils._chat(message)

    # The log record message should contain the Chinese characters as-is, not escaped
    found = False
    for record in caplog.records:
        if record.levelno == logging_utils.LEVEL_CHAT_SAVE:
            # The message is json.dumps(message, ensure_ascii=False)
            # So it should contain the Chinese characters directly
            if "测试中文字符" in record.getMessage() and "值" in record.getMessage():
                found = True
                # Also check that the message is valid JSON and not escaped
                loaded = json.loads(record.getMessage())
                assert loaded == message
    assert found, "Did not find log record with Chinese characters logged correctly"


def test_json_dumps_ensure_ascii_false_in_model_str_and_dict_dialog_agent(caplog):
    """
    Test that json.dumps calls in Model.__str__ and DictDialogAgent.reply use ensure_ascii=False,
    so Chinese characters are output as-is, not escaped.
    """
    import src.agentscope.models.model as model_module
    import src.agentscope.agents.dict_dialog_agent as dict_dialog_agent_module

    # Retrieve Model class safely
    Model = getattr(model_module, "Model", None)
    assert Model is not None, "Model class not found in src.agentscope.models.model"

    # Check Model.__str__ uses ensure_ascii=False
    # We test by creating a dummy subclass with known Chinese fields
    class DummyModel(Model):
        def __init__(self):
            # Minimal attributes to satisfy __str__
            self.name = "测试模型"
            self.config_name = "测试配置"
            self.description = "描述中文"
            self.image_urls = []
            self.raw = {"key": "值"}

    dummy = DummyModel()
    s = str(dummy)
    # The string should contain Chinese characters directly, not escaped unicode
    assert "测试模型" in s
    assert "描述中文" in s
    assert "值" in s
    # It should be valid JSON
    loaded = json.loads(s)
    assert loaded["name"] == "测试模型"
    assert loaded["description"] == "描述中文"
    assert loaded["raw"]["key"] == "值"

    # Check DictDialogAgent.reply logs JSON with ensure_ascii=False
    # We patch the logger to capture debug logs
    logger = logging.getLogger("agentscope")
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="agentscope")

    # Create a minimal DictDialogAgent instance with _call returning Chinese text
    class DummyAgent(dict_dialog_agent_module.DictDialogAgent):
        def __init__(self):
            # Provide minimal args to avoid errors
            super().__init__(name="dummy", use_memory=False)
            # Patch model attribute to avoid errors in PromptEngine init
            # Use environment variable for model_config_name to avoid None
            self.model = None
            # Patch engine attribute to avoid errors
            class DummyEngine:
                def join(self, *args):
                    return "prompt"
            self.engine = DummyEngine()
            self.memory = None
            self.sys_prompt = ""

        def _call(self, x):
            # Return dict with Chinese characters
            return {"speak": "中文日志测试", "extra": {"key": "值"}}

    agent = DummyAgent()
    # Call reply to trigger logging
    response = agent.reply({"input": "测试"})
    # Check that the debug log contains Chinese characters unescaped
    found = False
    for record in caplog.records:
        if record.levelno == logging.DEBUG:
            msg = record.getMessage()
            if "中文日志测试" in msg and "值" in msg:
                found = True
                # Also check that the message is valid JSON and not escaped
                try:
                    loaded = json.loads(msg)
                    assert loaded["speak"] == "中文日志测试"
                    assert loaded["extra"]["key"] == "值"
                except Exception:
                    pytest.fail("Logged message is not valid JSON")
    assert found, "Did not find debug log with Chinese characters logged correctly"


@pytest.mark.parametrize("json_func", [json.dumps])
def test_model_init_and_str_with_chinese(json_func):
    """
    Test that the Model class serializes to JSON with ensure_ascii=False,
    so that Chinese characters are output as-is, not escaped.
    """
    from src.agentscope.models import model as model_module

    Model = getattr(model_module, "Model", None)
    assert Model is not None, "Model class not found in src.agentscope.models.model"

    # Create a minimal subclass with Chinese characters
    class TestModel(Model):
        def __init__(self):
            self.name = "测试模型"
            self.config_name = "配置"
            self.description = "描述中文"
            self.image_urls = []
            self.raw = {"key": "值"}

    m = TestModel()
    s = str(m)
    # The string should contain Chinese characters directly, not escaped unicode
    assert "测试模型" in s
    assert "描述中文" in s
    assert "值" in s

    # The output should be valid JSON and match the fields
    loaded = json_func(s)
    # json_func returns string, so parse it again to dict
    loaded_dict = json.loads(loaded)
    assert loaded_dict["name"] == "测试模型"
    assert loaded_dict["description"] == "描述中文"
    assert loaded_dict["raw"]["key"] == "值"


def test_model_init_logs_kwargs_with_chinese(caplog):
    """
    Test that Model __init__ logs kwargs with ensure_ascii=False so Chinese chars appear correctly.
    """
    from src.agentscope.models import model as model_module

    Model = getattr(model_module, "Model", None)
    assert Model is not None, "Model class not found in src.agentscope.models.model"

    caplog.set_level(logging.DEBUG, logger="agentscope")

    # We instantiate Model with kwargs containing Chinese characters
    kwargs = {
        "param1": "值1",
        "param2": {"nested": "嵌套值"},
    }
    # The config_name is required
    m = Model(config_name="测试模型", **kwargs)

    # Check that debug log contains Chinese characters unescaped
    found = False
    for record in caplog.records:
        if record.levelno == logging.DEBUG:
            msg = record.getMessage()
            if "测试模型" in msg and "值1" in msg and "嵌套值" in msg:
                found = True
                # Also check that the logged JSON is valid and unescaped
                # Extract JSON part after the colon and newline
                json_part = msg.split("]:\n", 1)[-1]
                loaded = json.loads(json_part)
                assert loaded["param1"] == "值1"
                assert loaded["param2"]["nested"] == "嵌套值"
    assert found, "Did not find debug log with Chinese characters logged correctly"


def test_dict_dialog_agent_reply_logs_chinese_correctly():
    """
    Test that DictDialogAgent.reply logs the response JSON with ensure_ascii=False,
    so Chinese characters appear correctly in logs.
    """
    import src.agentscope.agents.dict_dialog_agent as dict_dialog_agent_module
    import logging

    caplog_records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            caplog_records.append(record)

    logger = logging.getLogger("agentscope")
    # Remove existing handlers and add capture handler
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    logger.addHandler(CaptureHandler())
    logger.setLevel(logging.DEBUG)

    class DummyMemory:
        def add(self, x):
            pass

        def get_memory(self):
            return []

    class DummyAgent(dict_dialog_agent_module.DictDialogAgent):
        def __init__(self):
            # Provide minimal required args to avoid AttributeError
            # Provide model_config_name to avoid None and model attribute error
            super().__init__(name="dummy", use_memory=False, model_config_name=os.getenv("MODEL", "default"))
            self.memory = DummyMemory()
            self.sys_prompt = ""
            # Patch model attribute to avoid AttributeError in PromptEngine init
            self.model = None
            class DummyEngine:
                def join(self, *args):
                    return "prompt"
            self.engine = DummyEngine()

        def _call(self, x):
            # Return a dict with Chinese characters
            return {"speak": "中文日志测试", "extra": {"key": "值"}}

    agent = DummyAgent()
    response = agent.reply({"input": "测试"})

    # Check that the captured logs contain the Chinese characters unescaped
    found = False
    for record in caplog_records:
        if record.levelno == logging.DEBUG:
            msg = record.getMessage()
            if "中文日志测试" in msg and "值" in msg:
                found = True
                # Also check that the logged message is valid JSON and contains expected keys
                try:
                    loaded = json.loads(msg)
                    assert loaded["speak"] == "中文日志测试"
                    assert loaded["extra"]["key"] == "值"
                except Exception:
                    assert False, "Logged message is not valid JSON"

    assert found, "Did not find debug log with Chinese characters logged correctly"