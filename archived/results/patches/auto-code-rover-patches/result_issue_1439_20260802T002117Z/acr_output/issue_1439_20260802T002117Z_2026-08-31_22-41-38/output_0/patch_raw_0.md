The problem is that ToolUsage internally creates its own default instance of I18N, which ignores any custom prompt files or language settings the agent or crew might have set. To fix this, ToolUsage should accept an i18n instance upon initialization and use that instead of always instantiating its own. This way, the localization and prompt_file settings remain consistent and updates to the prompt files get reflected correctly in error messages and other i18n usages within ToolUsage.

The fix involves:
- Adding an i18n parameter to ToolUsage.__init__, defaulting to None for backward compatibility.
- If an i18n instance is passed, assign it to self._i18n; otherwise, create a new instance.
- Modify CrewAgentExecutor._use_tool to pass its own i18n instance when creating ToolUsage.

This minimal change ensures existing usages won't break but fixes the issue for agents using a custom i18n instance.

---

# modification 1
```
<file>src/crewai/tools/tool_usage.py</file>
<original>    def __init__(
        self,
        tools_handler: ToolsHandler,
        tools: List[Any],
        original_tools: List[Any],
        tools_description: str,
        tools_names: str,
        task: Task,
        function_calling_llm: Any,
        agent: Any,
        action: Any,
    ) -> None:
        self._i18n: I18N = I18N()
        self._printer: Printer = Printer()
        self._telemetry: Telemetry = Telemetry()
        self._run_attempts: int = 1
        self._max_parsing_attempts: int = 3
        self._remember_format_after_usages: int = 3
        self.agent = agent
        self.tools_description = tools_description
        self.tools_names = tools_names
        self.tools_handler = tools_handler
        self.original_tools = original_tools
        self.tools = tools
        self.task = task
        self.action = action
        self.function_calling_llm = function_calling_llm

        # Set the maximum parsing attempts for bigger models
        if (
            self.function_calling_llm
            and self.function_calling_llm in OPENAI_BIGGER_MODELS
        ):
            self._max_parsing_attempts = 2
            self._remember_format_after_usages = 4
</original>
<patched>    def __init__(
        self,
        tools_handler: ToolsHandler,
        tools: List[Any],
        original_tools: List[Any],
        tools_description: str,
        tools_names: str,
        task: Task,
        function_calling_llm: Any,
        agent: Any,
        action: Any,
        i18n: I18N = None,
    ) -> None:
        self._i18n: I18N = i18n if i18n is not None else I18N()
        self._printer: Printer = Printer()
        self._telemetry: Telemetry = Telemetry()
        self._run_attempts: int = 1
        self._max_parsing_attempts: int = 3
        self._remember_format_after_usages: int = 3
        self.agent = agent
        self.tools_description = tools_description
        self.tools_names = tools_names
        self.tools_handler = tools_handler
        self.original_tools = original_tools
        self.tools = tools
        self.task = task
        self.action = action
        self.function_calling_llm = function_calling_llm

        # Set the maximum parsing attempts for bigger models
        if (
            self.function_calling_llm
            and self.function_calling_llm in OPENAI_BIGGER_MODELS
        ):
            self._max_parsing_attempts = 2
            self._remember_format_after_usages = 4
</patched>
```

# modification 2
```
<file>src/crewai/agents/crew_agent_executor.py</file>
<original>    def _use_tool(self, agent_action: AgentAction) -> Any:
        tool_usage = ToolUsage(
            tools_handler=self.tools_handler,
            tools=self.tools,
            original_tools=self.original_tools,
            tools_description=self.tools_description,
            tools_names=self.tools_names,
            function_calling_llm=self.function_calling_llm,
            task=self.task,  # type: ignore[arg-type]
            agent=self.agent,
            action=agent_action,
        )
        tool_calling = tool_usage.parse(agent_action.text)

        if isinstance(tool_calling, ToolUsageErrorException):
            tool_result = tool_calling.message
        else:
            if tool_calling.tool_name.casefold().strip() in [
                name.casefold().strip() for name in self.name_to_tool_map
            ] or tool_calling.tool_name.casefold().replace("_", " ") in [
                name.casefold().strip() for name in self.name_to_tool_map
            ]:
                tool_result = tool_usage.use(tool_calling, agent_action.text)
            else:
                tool_result = self._i18n.errors("wrong_tool_name").format(
                    tool=tool_calling.tool_name,
                    tools=", ".join([tool.name.casefold() for tool in self.tools]),
                )
        return tool_result
</original>
<patched>    def _use_tool(self, agent_action: AgentAction) -> Any:
        tool_usage = ToolUsage(
            tools_handler=self.tools_handler,
            tools=self.tools,
            original_tools=self.original_tools,
            tools_description=self.tools_description,
            tools_names=self.tools_names,
            function_calling_llm=self.function_calling_llm,
            task=self.task,  # type: ignore[arg-type]
            agent=self.agent,
            action=agent_action,
            i18n=self._i18n,
        )
        tool_calling = tool_usage.parse(agent_action.text)

        if isinstance(tool_calling, ToolUsageErrorException):
            tool_result = tool_calling.message
        else:
            if tool_calling.tool_name.casefold().strip() in [
                name.casefold().strip() for name in self.name_to_tool_map
            ] or tool_calling.tool_name.casefold().replace("_", " ") in [
                name.casefold().strip() for name in self.name_to_tool_map
            ]:
                tool_result = tool_usage.use(tool_calling, agent_action.text)
            else:
                tool_result = self._i18n.errors("wrong_tool_name").format(
                    tool=tool_calling.tool_name,
                    tools=", ".join([tool.name.casefold() for tool in self.tools]),
                )
        return tool_result
</patched>
```