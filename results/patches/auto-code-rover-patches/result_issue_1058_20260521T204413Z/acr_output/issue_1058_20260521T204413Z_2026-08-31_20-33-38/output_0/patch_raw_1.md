The root cause of the issue is that `_json_loads_with_repair` is called prematurely on partial, incomplete JSON fragments in streamed tool calls, especially when those fragments include multiline strings or special characters. This leads to hang or crash because the repair function tries to fix incomplete JSON repeatedly or fails.

The solution is to delay JSON parsing/repair until the entire content is received (i.e., detect the final chunk for each tool call argument). Since the streaming API provides incremental updates, we must buffer partial tool-call arguments keyed by their index, and only parse them when the final relevant chunk is observed (when `chunk.output.last` or equivalent is True).

In context of `_parse_dashscope_stream_response`, we will change the logic to:
- Buffer tool call arguments in a dict with index keys.
- Only attempt `_json_loads_with_repair` after confirming the message chunk is the final part of the stream (`chunk.output.last` is True).
- Until then, treat tool call arguments as raw strings to avoid premature parsing.

All the other aggregation of chat content and thinking content remains unchanged.

No changes are needed to the non-streaming `_parse_dashscope_generation_response` as it operates on complete responses.

---

# modification 1
```
<file>src/agentscope/model/_dashscope_model.py</file>
<original>    async def _parse_dashscope_stream_response(
        self,
        start_datetime: datetime,
        response: Union[
            AsyncGenerator[GenerationResponse, None],
            Generator[MultiModalConversationResponse, None, None],
        ],
        structured_model: Type[BaseModel] | None = None,
    ) -> AsyncGenerator[ChatResponse, Any]:
        """Given a DashScope streaming response generator, extract the content
            blocks and usages from it and yield ChatResponse objects.

        Args:
            start_datetime (`datetime`):
                The start datetime of the response generation.
            response (
                `Union[AsyncGenerator[GenerationResponse, None], Generator[ \
                MultiModalConversationResponse, None, None]]`
            ):
                DashScope streaming response generator (GenerationResponse or
                MultiModalConversationResponse) to parse.
            structured_model (`Type[BaseModel] | None`, default `None`):
                A Pydantic BaseModel class that defines the expected structure
                for the model's output.

        Returns:
            AsyncGenerator[ChatResponse, Any]:
                An async generator that yields ChatResponse objects containing
                the content blocks and usage information for each chunk in the
                streaming response.

        .. note::
            If `structured_model` is not `None`, the expected structured output
            will be stored in the metadata of the `ChatResponse`.
        """
        acc_content, acc_thinking_content = "", ""
        acc_tool_calls = collections.defaultdict(dict)
        metadata = None

        async for chunk in giter(response):
            if chunk.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"Failed to get response from _ API: {chunk}",
                )

            message = chunk.output.choices[0].message

            # Update reasoning content
            if isinstance(message.get("reasoning_content"), str):
                acc_thinking_content += message["reasoning_content"]

            # Update text content
            if isinstance(message.content, str):
                acc_content += message.content
            elif isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict) and "text" in item:
                        acc_content += item["text"]

            # Update tool calls
            for tool_call in message.get("tool_calls", []):
                index = tool_call.get("index", 0)

                if "id" in tool_call and tool_call["id"] != acc_tool_calls[
                    index
                ].get("id"):
                    acc_tool_calls[index]["id"] = (
                        acc_tool_calls[index].get("id", "") + tool_call["id"]
                    )

                if "function" in tool_call:
                    func = tool_call["function"]
                    if "name" in func:
                        acc_tool_calls[index]["name"] = (
                            acc_tool_calls[index].get("name", "")
                            + func["name"]
                        )

                    if "arguments" in func:
                        acc_tool_calls[index]["arguments"] = (
                            acc_tool_calls[index].get("arguments", "")
                            + func["arguments"]
                        )

            # to content blocks
            content_blocks: list[TextBlock | ToolUseBlock | ThinkingBlock] = []
            if acc_thinking_content:
                content_blocks.append(
                    ThinkingBlock(
                        type="thinking",
                        thinking=acc_thinking_content,
                    ),
                )

            if acc_content:
                content_blocks.append(
                    TextBlock(
                        type="text",
                        text=acc_content,
                    ),
                )

            for tool_call in acc_tool_calls.values():
                repaired_input = _json_loads_with_repair(
                    tool_call.get("arguments", "{}") or "{}",
                )

                if not isinstance(repaired_input, dict):
                    repaired_input = {}

                content_blocks.append(
                    ToolUseBlock(
                        type="tool_use",
                        id=tool_call.get("id", ""),
                        name=tool_call.get("name", ""),
                        input=repaired_input,
                    ),
                )

                if structured_model:
                    metadata = repaired_input

            usage = None
            if chunk.usage:
                usage = ChatUsage(
                    input_tokens=chunk.usage.input_tokens,
                    output_tokens=chunk.usage.output_tokens,
                    time=(datetime.now() - start_datetime).total_seconds(),
                    metadata=chunk.usage,
                )

            parsed_chunk = ChatResponse(
                content=content_blocks,
                usage=usage,
                metadata=metadata,
            )
            yield parsed_chunk
</original>
<patched>    async def _parse_dashscope_stream_response(
        self,
        start_datetime: datetime,
        response: Union[
            AsyncGenerator[GenerationResponse, None],
            Generator[MultiModalConversationResponse, None, None],
        ],
        structured_model: Type[BaseModel] | None = None,
    ) -> AsyncGenerator[ChatResponse, Any]:
        """Given a DashScope streaming response generator, extract the content
            blocks and usages from it and yield ChatResponse objects.

        Args:
            start_datetime (`datetime`):
                The start datetime of the response generation.
            response (
                `Union[AsyncGenerator[GenerationResponse, None], Generator[ \
                MultiModalConversationResponse, None, None]]`
            ):
                DashScope streaming response generator (GenerationResponse or
                MultiModalConversationResponse) to parse.
            structured_model (`Type[BaseModel] | None`, default `None`):
                A Pydantic BaseModel class that defines the expected structure
                for the model's output.

        Returns:
            AsyncGenerator[ChatResponse, Any]:
                An async generator that yields ChatResponse objects containing
                the content blocks and usage information for each chunk in the
                streaming response.

        .. note::
            If `structured_model` is not `None`, the expected structured output
            will be stored in the metadata of the `ChatResponse`.
        """
        acc_content, acc_thinking_content = "", ""
        acc_tool_calls = collections.defaultdict(dict)
        metadata = None

        # Buffer for tool call arguments partial content, keyed by index
        buffered_arguments = collections.defaultdict(str)
        # Track tool call ids and names for each index separately for last chunk assignment
        tool_call_ids = {}
        tool_call_names = {}

        async for chunk in giter(response):
            if chunk.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"Failed to get response from _ API: {chunk}",
                )

            message = chunk.output.choices[0].message

            # Update reasoning content
            if isinstance(message.get("reasoning_content"), str):
                acc_thinking_content += message["reasoning_content"]

            # Update text content
            if isinstance(message.content, str):
                acc_content += message.content
            elif isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict) and "text" in item:
                        acc_content += item["text"]

            # Update tool calls
            for tool_call in message.get("tool_calls", []):
                index = tool_call.get("index", 0)

                # Update tool call id and name for the last chunk
                if "id" in tool_call:
                    tool_call_ids[index] = tool_call["id"]
                if "function" in tool_call:
                    func = tool_call["function"]
                    if "name" in func:
                        tool_call_names[index] = func["name"]

                    if "arguments" in func:
                        # Buffer the arguments incrementally per index
                        buffered_arguments[index] += func["arguments"]

            # when the chunk is the last in the stream, finalize tool call inputs
            content_blocks: list[TextBlock | ToolUseBlock | ThinkingBlock] = []
            if acc_thinking_content:
                content_blocks.append(
                    ThinkingBlock(
                        type="thinking",
                        thinking=acc_thinking_content,
                    ),
                )

            if acc_content:
                content_blocks.append(
                    TextBlock(
                        type="text",
                        text=acc_content,
                    ),
                )

            # Only parse/repair tool call arguments on last chunk to avoid hanging on partial JSON
            is_last_chunk = getattr(chunk.output, "last", False)
            if is_last_chunk:
                for index, arguments_str in buffered_arguments.items():
                    repaired_input = _json_loads_with_repair(arguments_str or "{}")

                    if not isinstance(repaired_input, dict):
                        repaired_input = {}

                    content_blocks.append(
                        ToolUseBlock(
                            type="tool_use",
                            id=tool_call_ids.get(index, ""),
                            name=tool_call_names.get(index, ""),
                            input=repaired_input,
                        ),
                    )

                    if structured_model:
                        metadata = repaired_input

            usage = None
            if chunk.usage:
                usage = ChatUsage(
                    input_tokens=chunk.usage.input_tokens,
                    output_tokens=chunk.usage.output_tokens,
                    time=(datetime.now() - start_datetime).total_seconds(),
                    metadata=chunk.usage,
                )

            parsed_chunk = ChatResponse(
                content=content_blocks,
                usage=usage,
                metadata=metadata,
            )
            yield parsed_chunk
</patched>
```