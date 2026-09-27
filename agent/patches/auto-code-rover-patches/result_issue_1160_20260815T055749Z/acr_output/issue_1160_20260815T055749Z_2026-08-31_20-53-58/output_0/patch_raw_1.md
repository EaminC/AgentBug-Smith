The core of the issue lies in how the summary messages are generated and subsequently inserted back into the conversation history. When using structured output models, the agent responses contain `toolUse` blocks, which are not allowed in user messages when calling AWS Bedrock's ConverseStream API. The root cause is that the summarization methods `_generate_summary_with_agent` and `_generate_summary_with_model` take the agent's summary response—which may include toolUses—and directly cast them to user messages without stripping or sanitizing the `toolUse` content.

To fix this, we should add a helper method to sanitize the message by removing any `toolUse` blocks from the content and thus produce a valid user message that complies with AWS Bedrock API rules. Then, both `_generate_summary_with_agent` and `_generate_summary_with_model` should apply this sanitization before returning the summary message.

This approach keeps the existing summarization logic and outputs as unchanged as possible but ensures compliance with the API constraints by removing problematic content before the summary is inserted back as a user message.

---

# modification 1

```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>    def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
        """Generate a summary using the dedicated summarization agent.

        Args:
            messages: The messages to summarize.

        Returns:
            A message containing the conversation summary.
        """
        summarization_agent = self.summarization_agent
        assert summarization_agent is not None  # guaranteed by caller

        original_system_prompt = summarization_agent.system_prompt
        original_messages = summarization_agent.messages.copy()
        original_tool_registry = summarization_agent.tool_registry

        try:
            # Add no-op tool if agent has no tools to satisfy tool spec requirement
            if not summarization_agent.tool_names:
                tool_registry = ToolRegistry()
                tool_registry.register_tool(cast(AgentTool, noop_tool))
                summarization_agent.tool_registry = tool_registry

            summarization_agent.messages = messages

            result = summarization_agent("Please summarize this conversation.")
            return cast(Message, {**result.message, "role": "user"})

        finally:
            summarization_agent.system_prompt = original_system_prompt
            summarization_agent.messages = original_messages
            summarization_agent.tool_registry = original_tool_registry
</original>
<patched>    def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
        """Generate a summary using the dedicated summarization agent.

        Args:
            messages: The messages to summarize.

        Returns:
            A message containing the conversation summary.
        """
        summarization_agent = self.summarization_agent
        assert summarization_agent is not None  # guaranteed by caller

        original_system_prompt = summarization_agent.system_prompt
        original_messages = summarization_agent.messages.copy()
        original_tool_registry = summarization_agent.tool_registry

        try:
            # Add no-op tool if agent has no tools to satisfy tool spec requirement
            if not summarization_agent.tool_names:
                tool_registry = ToolRegistry()
                tool_registry.register_tool(cast(AgentTool, noop_tool))
                summarization_agent.tool_registry = tool_registry

            summarization_agent.messages = messages

            result = summarization_agent("Please summarize this conversation.")
            sanitized_message = self._sanitize_summary_message(result.message)
            return sanitized_message

        finally:
            summarization_agent.system_prompt = original_system_prompt
            summarization_agent.messages = original_messages
            summarization_agent.tool_registry = original_tool_registry
</patched>
```

# modification 2

```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>    def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
        """Generate a summary by calling the agent's model directly.

        This bypasses the full agent pipeline (lock, metrics, traces, tool loop) and
        simply asks the underlying model to summarize the conversation.

        Args:
            messages: The messages to summarize.
            agent: The parent agent whose model is used.

        Returns:
            A message containing the conversation summary.
        """
        system_prompt = (
            self.summarization_system_prompt
            if self.summarization_system_prompt is not None
            else DEFAULT_SUMMARIZATION_PROMPT
        )

        # Build the message list: conversation history + summarization request
        summarization_messages = list(messages) + [
            {"role": "user", "content": [{"text": "Please summarize this conversation."}]}
        ]

        async def _call_model() -> Message:
            chunks = agent.model.stream(
                summarization_messages,
                tool_specs=None,
                system_prompt=system_prompt,
            )

            result_message: Message | None = None
            async for event in process_stream(chunks):
                if "stop" in event:
                    _, result_message, _, _ = event["stop"]

            if result_message is None:
                raise RuntimeError("Failed to generate summary: no response from model")
            return result_message

        message = run_async(_call_model)
        return cast(Message, {**message, "role": "user"})</original>
<patched>    def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
        """Generate a summary by calling the agent's model directly.

        This bypasses the full agent pipeline (lock, metrics, traces, tool loop) and
        simply asks the underlying model to summarize the conversation.

        Args:
            messages: The messages to summarize.
            agent: The parent agent whose model is used.

        Returns:
            A message containing the conversation summary.
        """
        system_prompt = (
            self.summarization_system_prompt
            if self.summarization_system_prompt is not None
            else DEFAULT_SUMMARIZATION_PROMPT
        )

        # Build the message list: conversation history + summarization request
        summarization_messages = list(messages) + [
            {"role": "user", "content": [{"text": "Please summarize this conversation."}]}
        ]

        async def _call_model() -> Message:
            chunks = agent.model.stream(
                summarization_messages,
                tool_specs=None,
                system_prompt=system_prompt,
            )

            result_message: Message | None = None
            async for event in process_stream(chunks):
                if "stop" in event:
                    _, result_message, _, _ = event["stop"]

            if result_message is None:
                raise RuntimeError("Failed to generate summary: no response from model")
            return result_message

        message = run_async(_call_model)
        sanitized_message = self._sanitize_summary_message(message)
        return sanitized_message
</patched>
```

# modification 3

```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>class SummarizingConversationManager(ConversationManager):
    """Implements a summarizing window manager.

    This manager provides a configurable option to summarize older context instead of
    simply trimming it, helping preserve important information while staying within
    context limits.
    """
    ...
    def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
        ...
    def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
        ...
    def _adjust_split_point_for_tool_pairs(self, messages: list[Message], split_point: int) -> int:
        ...
</original>
<patched>class SummarizingConversationManager(ConversationManager):
    """Implements a summarizing window manager.

    This manager provides a configurable option to summarize older context instead of
    simply trimming it, helping preserve important information while staying within
    context limits.
    """
    ...
    def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
        ...
    def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
        ...
    def _adjust_split_point_for_tool_pairs(self, messages: list[Message], split_point: int) -> int:
        ...

    def _sanitize_summary_message(self, message: Message) -> Message:
        """Sanitize the summary message to remove any 'toolUse' content to comply with AWS Bedrock user message restrictions.

        Args:
            message: The message to sanitize.

        Returns:
            The sanitized message with role set to 'user' and no 'toolUse' content.
        """
        # Deepcopy to avoid mutation side effects
        from copy import deepcopy

        sanitized = deepcopy(message)
        sanitized["role"] = "user"

        # Filter content to exclude any dict with 'toolUse' key
        filtered_content = []
        for item in sanitized.get("content", []):
            if not (isinstance(item, dict) and "toolUse" in item):
                filtered_content.append(item)
        sanitized["content"] = filtered_content

        return sanitized
</patched>
```

---

Summary:

- Added a `_sanitize_summary_message` method to clean toolUse content.
- Applied this sanitization in both `_generate_summary_with_agent` and `_generate_summary_with_model` before returning.
- This avoids user messages with disallowed toolUse content, preventing the ValidationException.