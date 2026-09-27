The root cause of the ValidationException is that when the summarization is done with a dedicated summarization agent or by directly calling the model, the resulting summary message might still contain `toolUse` blocks. According to AWS Bedrock API rules, user messages are not allowed to contain `toolUse` blocks. The existing SummarizingConversationManager converts the assistant's message (which may have tools) to a user message when returning the summary, but does not sanitize or remove toolUse content, causing invalid user messages and triggering validation errors.

To fix this issue, we need to sanitize the message returned by the summarization calls to remove all toolUse contents from the message, leaving only the text or toolResult content allowed for user messages. We will add a helper method `_sanitize_user_message` that removes toolUse blocks from a message's content and ensures it's valid for a user role. We will then use this sanitizer in both `_generate_summary_with_agent` and `_generate_summary_with_model` methods before returning the summary message as a user message.

This approach preserves the original summarization logic and output while preventing invalid user messages containing toolUse from being passed to the Converse API, hence preventing the ValidationException.

---

# modification 1
```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>212     def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
213         """Generate a summary using the dedicated summarization agent.
214
215         Args:
216             messages: The messages to summarize.
217
218         Returns:
219             A message containing the conversation summary.
220         """
221         summarization_agent = self.summarization_agent
222         assert summarization_agent is not None  # guaranteed by caller
223
224         original_system_prompt = summarization_agent.system_prompt
225         original_messages = summarization_agent.messages.copy()
226         original_tool_registry = summarization_agent.tool_registry
227
228         try:
229             # Add no-op tool if agent has no tools to satisfy tool spec requirement
230             if not summarization_agent.tool_names:
231                 tool_registry = ToolRegistry()
232                 tool_registry.register_tool(cast(AgentTool, noop_tool))
233                 summarization_agent.tool_registry = tool_registry
234
235             summarization_agent.messages = messages
236
237             result = summarization_agent("Please summarize this conversation.")
238             return cast(Message, {**result.message, "role": "user"})
239
240         finally:
241             summarization_agent.system_prompt = original_system_prompt
242             summarization_agent.messages = original_messages
243             summarization_agent.tool_registry = original_tool_registry
244 </original>
<patched>212     def _generate_summary_with_agent(self, messages: list[Message]) -> Message:
213         """Generate a summary using the dedicated summarization agent.
214
215         Args:
216             messages: The messages to summarize.
217
218         Returns:
219             A message containing the conversation summary.
220         """
221         summarization_agent = self.summarization_agent
222         assert summarization_agent is not None  # guaranteed by caller
223
224         original_system_prompt = summarization_agent.system_prompt
225         original_messages = summarization_agent.messages.copy()
226         original_tool_registry = summarization_agent.tool_registry
227
228         try:
229             # Add no-op tool if agent has no tools to satisfy tool spec requirement
230             if not summarization_agent.tool_names:
231                 tool_registry = ToolRegistry()
232                 tool_registry.register_tool(cast(AgentTool, noop_tool))
233                 summarization_agent.tool_registry = tool_registry
234
235             summarization_agent.messages = messages
236
237             result = summarization_agent("Please summarize this conversation.")
238             sanitized_message = self._sanitize_user_message(result.message)
239             return cast(Message, {**sanitized_message, "role": "user"})
240
241         finally:
242             summarization_agent.system_prompt = original_system_prompt
243             summarization_agent.messages = original_messages
244             summarization_agent.tool_registry = original_tool_registry
244 </patched>
```

# modification 2
```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>245     def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
246         """Generate a summary by calling the agent's model directly.
247
248         This bypasses the full agent pipeline (lock, metrics, traces, tool loop) and
249         simply asks the underlying model to summarize the conversation.
250
251         Args:
252             messages: The messages to summarize.
253             agent: The parent agent whose model is used.
254
255         Returns:
256             A message containing the conversation summary.
257         """
258         system_prompt = (
259             self.summarization_system_prompt
260             if self.summarization_system_prompt is not None
261             else DEFAULT_SUMMARIZATION_PROMPT
262         )
263
264         # Build the message list: conversation history + summarization request
265         summarization_messages = list(messages) + [
266             {"role": "user", "content": [{"text": "Please summarize this conversation."}]}
267         ]
268
269         async def _call_model() -> Message:
270             chunks = agent.model.stream(
271                 summarization_messages,
272                 tool_specs=None,
273                 system_prompt=system_prompt,
274             )
275
276             result_message: Message | None = None
277             async for event in process_stream(chunks):
278                 if "stop" in event:
279                     _, result_message, _, _ = event["stop"]
280
281             if result_message is None:
282                 raise RuntimeError("Failed to generate summary: no response from model")
283             return result_message
284
285         message = run_async(_call_model)
286         return cast(Message, {**message, "role": "user"})
</original>
<patched>245     def _generate_summary_with_model(self, messages: list[Message], agent: "Agent") -> Message:
246         """Generate a summary by calling the agent's model directly.
247
248         This bypasses the full agent pipeline (lock, metrics, traces, tool loop) and
249         simply asks the underlying model to summarize the conversation.
250
251         Args:
252             messages: The messages to summarize.
253             agent: The parent agent whose model is used.
254
255         Returns:
256             A message containing the conversation summary.
257         """
258         system_prompt = (
259             self.summarization_system_prompt
260             if self.summarization_system_prompt is not None
261             else DEFAULT_SUMMARIZATION_PROMPT
262         )
263
264         # Build the message list: conversation history + summarization request
265         summarization_messages = list(messages) + [
266             {"role": "user", "content": [{"text": "Please summarize this conversation."}]}
267         ]
268
269         async def _call_model() -> Message:
270             chunks = agent.model.stream(
271                 summarization_messages,
272                 tool_specs=None,
273                 system_prompt=system_prompt,
274             )
275
276             result_message: Message | None = None
277             async for event in process_stream(chunks):
278                 if "stop" in event:
279                     _, result_message, _, _ = event["stop"]
280
281             if result_message is None:
282                 raise RuntimeError("Failed to generate summary: no response from model")
283             return result_message
284
285         message = run_async(_call_model)
286         sanitized_message = self._sanitize_user_message(message)
287         return cast(Message, {**sanitized_message, "role": "user"})
</patched>
```

# modification 3
```
<file>src/strands/agent/conversation_manager/summarizing_conversation_manager.py</file>
<original>54 class SummarizingConversationManager(ConversationManager):
55     """Implements a summarizing window manager.
56
57     This manager provides a configurable option to summarize older context instead of
58     simply trimming it, helping preserve important information while staying within
59     context limits.
60     """
61
62     def __init__(
63         self,
64         summary_ratio: float = 0.3,
65         preserve_recent_messages: int = 10,
66         summarization_agent: Optional["Agent"] = None,
67         summarization_system_prompt: str | None = None,
68     ):
69         """Initialize the summarizing conversation manager.
70
71         Args:
72             summary_ratio: Ratio of messages to summarize vs keep when context overflow occurs.
73                 Value between 0.1 and 0.8. Defaults to 0.3 (summarize 30% of oldest messages).
74             preserve_recent_messages: Minimum number of recent messages to always keep.
75                 Defaults to 10 messages.
76             summarization_agent: Optional agent to use for summarization instead of the parent agent.
77                 If provided, this agent can use tools as part of the summarization process.
78             summarization_system_prompt: Optional system prompt override for summarization.
79                 If None, uses the default summarization prompt.
80         """
81         super().__init__()
82         if summarization_agent is not None and summarization_system_prompt is not None:
83             raise ValueError(
84                 "Cannot provide both summarization_agent and summarization_system_prompt. "
85                 "Agents come with their own system prompt."
86             )
87
88         self.summary_ratio = max(0.1, min(0.8, summary_ratio))
89         self.preserve_recent_messages = preserve_recent_messages
90         self.summarization_agent = summarization_agent
91         self.summarization_system_prompt = summarization_system_prompt
92         self._summary_message: Message | None = None
</original>
<patched>54 class SummarizingConversationManager(ConversationManager):
55     """Implements a summarizing window manager.
56
57     This manager provides a configurable option to summarize older context instead of
58     simply trimming it, helping preserve important information while staying within
59     context limits.
60     """
61
62     def __init__(
63         self,
64         summary_ratio: float = 0.3,
65         preserve_recent_messages: int = 10,
66         summarization_agent: Optional["Agent"] = None,
67         summarization_system_prompt: str | None = None,
68     ):
69         """Initialize the summarizing conversation manager.
70
71         Args:
72             summary_ratio: Ratio of messages to summarize vs keep when context overflow occurs.
73                 Value between 0.1 and 0.8. Defaults to 0.3 (summarize 30% of oldest messages).
74             preserve_recent_messages: Minimum number of recent messages to always keep.
75                 Defaults to 10 messages.
76             summarization_agent: Optional agent to use for summarization instead of the parent agent.
77                 If provided, this agent can use tools as part of the summarization process.
78             summarization_system_prompt: Optional system prompt override for summarization.
79                 If None, uses the default summarization prompt.
80         """
81         super().__init__()
82         if summarization_agent is not None and summarization_system_prompt is not None:
83             raise ValueError(
84                 "Cannot provide both summarization_agent and summarization_system_prompt. "
85                 "Agents come with their own system prompt."
86             )
87
88         self.summary_ratio = max(0.1, min(0.8, summary_ratio))
89         self.preserve_recent_messages = preserve_recent_messages
90         self.summarization_agent = summarization_agent
91         self.summarization_system_prompt = summarization_system_prompt
92         self._summary_message: Message | None = None
93
94     def _sanitize_user_message(self, message: Message) -> Message:
95         """Remove or transform any toolUse content in a message to make it valid for user role."""
96         sanitized_content = []
97         for content_element in message.get("content", []):
98             # It's a dict representing a content block; only keep non-toolUse content
99             if "toolUse" in content_element:
100                 # Skip toolUse content as not allowed in user messages
101                 continue
102             # Keep all other content blocks (text, toolResult, etc)
103             sanitized_content.append(content_element)
104
105         # Return a copy of the message with sanitized content, role unset here because caller sets role user
106         return {**message, "content": sanitized_content}
</patched>
```