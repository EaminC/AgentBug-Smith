import pytest
from typing import Any, Dict

from crewai.tools.tool_usage import ToolUsage


class DummyI18N:
    def __init__(self, messages: Dict[str, str]):
        self._messages = messages

    def translate(self, key: str, **kwargs) -> str:
        # Return the custom message if available, else a default message
        return self._messages.get(key, f"default translation for {key}")


class DummyAgent:
    def __init__(self, i18n: DummyI18N):
        self.i18n = i18n


class DummyAction:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name


class DummyToolsHandler:
    pass


class DummyTask:
    pass


@pytest.mark.parametrize("use_custom_i18n", [True, False])
def test_toolusage_uses_agent_i18n_for_error_message(use_custom_i18n):
    """
    This test verifies that ToolUsage uses the same I18N instance as the agent,
    so that custom prompt_file translations are respected in tool error messages.

    Steps:
    1. Create a dummy i18n with a custom translation for 'tool_usage_exception'.
    2. Create a dummy agent with this i18n.
    3. Create a ToolUsage instance with this agent.
    4. Trigger a tool usage error message.
    5. Assert that the error message contains the custom translation text if using custom i18n,
       or the default translation if not.

    On the buggy codebase, ToolUsage uses a default I18N() ignoring the agent's i18n,
    so the custom translation will NOT appear, causing this test to fail.
    After the fix, ToolUsage uses agent.i18n, so the custom translation appears,
    making this test pass.
    """

    # Custom translation message to detect usage of the correct i18n
    custom_error_message = "Custom tool usage error message"

    # Create dummy i18n with custom translation for 'tool_usage_exception' or empty messages
    if use_custom_i18n:
        dummy_i18n = DummyI18N(messages={"tool_usage_exception": custom_error_message})
    else:
        dummy_i18n = DummyI18N(messages={})

    # Create dummy agent with this i18n
    dummy_agent = DummyAgent(i18n=dummy_i18n)

    # Create dummy action/tool name
    dummy_action = DummyAction(tool_name="dummy_tool")

    # Create dummy tools_handler, tools, original_tools, tools_description, tools_names, task, function_calling_llm
    dummy_tools_handler = DummyToolsHandler()
    dummy_tools = []
    dummy_original_tools = []
    dummy_tools_description = {}
    dummy_tools_names = []
    dummy_task = DummyTask()
    dummy_function_calling_llm = False

    # Create ToolUsage instance with dummy agent and action and required arguments
    tool_usage = ToolUsage(
        agent=dummy_agent,
        action=dummy_action,
        tools_handler=dummy_tools_handler,
        tools=dummy_tools,
        original_tools=dummy_original_tools,
        tools_description=dummy_tools_description,
        tools_names=dummy_tools_names,
        task=dummy_task,
        function_calling_llm=dummy_function_calling_llm,
    )

    # Compose an error message using ToolUsage's internal i18n
    # The key for translation is 'tool_usage_exception'
    error_message = tool_usage._i18n.translate("tool_usage_exception")

    if use_custom_i18n:
        # The error message should contain the custom translation text
        assert error_message == custom_error_message, (
            "ToolUsage did not use the agent's i18n for error message translation."
        )
    else:
        # The error message should be the default translation (not the custom one)
        assert error_message != custom_error_message, (
            "ToolUsage incorrectly used a custom translation when none was provided."
        )
