The problem is that the OpenAIModel's error handling currently only transforms `openai.BadRequestError` exceptions with a specific code ("context_length_exceeded") into `ContextWindowOverflowException`. However, when using OpenAI-compatible APIs that wrap Bedrock models (e.g., Databricks), context overflow errors come back as `openai.APIError` exceptions with messages containing certain phrases indicating context overflow. These errors are not currently caught and translated, leading to crashes rather than graceful context management.

To fix this, we need to extend the exception handling in the `stream` and `structured_output` methods to also catch `openai.APIError` (which is more generic than `BadRequestError`), check the error message for known Bedrock context overflow indicators, and convert them to `ContextWindowOverflowException`. This change must preserve existing behavior for other error types.

Specifically, I will:
1. Import `openai.APIError` to catch it.
2. Define a tuple of known error message substrings used by Bedrock indicating context overflow.
3. In `stream` and `structured_output` methods, add a catch block for `openai.APIError` after the existing handlers.
4. Check if the error message contains any known Bedrock context overflow phrases.
5. Raise `ContextWindowOverflowException` if matched, else re-raise.

This approach preserves backward compatibility with native OpenAI errors and handles Bedrock-style errors gracefully.

---

# modification 1
```
<file>src/strands/models/openai.py</file>
<original>import json
import base64
import mimetypes
import logging

from typing import Any, AsyncGenerator, AsyncIterator, TypedDict, cast
from typing_extensions import Unpack, override

import openai
from openai import Client
from openai.error import BadRequestError, RateLimitError

from ...exceptions import ContextWindowOverflowException, ModelThrottledException
from ...types import ContentBlock, Messages, StreamEvent, SystemContentBlock, ToolChoice, ToolResult, ToolSpec, ToolUse
from .._model import Model
from .._parsers import ParsedChatCompletion
from contextlib import asynccontextmanager
</original>
<patched>import json
import base64
import mimetypes
import logging

from typing import Any, AsyncGenerator, AsyncIterator, TypedDict, cast
from typing_extensions import Unpack, override

import openai
from openai import Client
from openai.error import BadRequestError, RateLimitError, APIError

from ...exceptions import ContextWindowOverflowException, ModelThrottledException
from ...types import ContentBlock, Messages, StreamEvent, SystemContentBlock, ToolChoice, ToolResult, ToolSpec, ToolUse
from .._model import Model
from .._parsers import ParsedChatCompletion
from contextlib import asynccontextmanager
</patched>
```

# modification 2
```
<file>src/strands/models/openai.py</file>
<original>    @override
    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream conversation with the OpenAI model.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Formatted message chunks from the model.

        Raises:
            ContextWindowOverflowException: If the input exceeds the model's context window.
            ModelThrottledException: If the request is throttled by OpenAI (rate limits).
        """
        logger.debug("formatting request")
        request = self.format_request(messages, tool_specs, system_prompt, tool_choice)
        logger.debug("formatted request=<%s>", request)

        logger.debug("invoking model")

        # We initialize an OpenAI context on every request so as to avoid connection sharing in the underlying httpx
        # client. The asyncio event loop does not allow connections to be shared. For more details, please refer to
        # https://github.com/encode/httpx/discussions/2959.
        async with self._get_client() as client:
            try:
                response = await client.chat.completions.create(**request)
            except openai.BadRequestError as e:
                # Check if this is a context length exceeded error
                if hasattr(e, "code") and e.code == "context_length_exceeded":
                    logger.warning("OpenAI threw context window overflow error")
                    raise ContextWindowOverflowException(str(e)) from e
                # Re-raise other BadRequestError exceptions
                raise
            except openai.RateLimitError as e:
                # All rate limit errors should be treated as throttling, not context overflow
                # Rate limits (including TPM) require waiting/retrying, not context reduction
                logger.warning("OpenAI threw rate limit error")
                raise ModelThrottledException(str(e)) from e

            logger.debug("got response from model")
            yield self.format_chunk({"chunk_type": "message_start"})
            tool_calls: dict[int, list[Any]] = {}
            data_type = None
            finish_reason = None  # Store finish_reason for later use
            event = None  # Initialize for scope safety

            async for event in response:
                # Defensive: skip events with empty or missing choices
                if not getattr(event, "choices", None):
                    continue
                choice = event.choices[0]

                if hasattr(choice.delta, "reasoning_content") and choice.delta.reasoning_content:
                    chunks, data_type = self._stream_switch_content("reasoning_content", data_type)
                    for chunk in chunks:
                        yield chunk
                    yield self.format_chunk(
                        {
                            "chunk_type": "content_delta",
                            "data_type": data_type,
                            "data": choice.delta.reasoning_content,
                        }
                    )

                if choice.delta.content:
                    chunks, data_type = self._stream_switch_content("text", data_type)
                    for chunk in chunks:
                        yield chunk
                    yield self.format_chunk(
                        {"chunk_type": "content_delta", "data_type": data_type, "data": choice.delta.content}
                    )

                for tool_call in choice.delta.tool_calls or []:
                    tool_calls.setdefault(tool_call.index, []).append(tool_call)

                if choice.finish_reason:
                    finish_reason = choice.finish_reason  # Store for use outside loop
                    if data_type:
                        yield self.format_chunk({"chunk_type": "content_stop", "data_type": data_type})
                    break

            for tool_deltas in tool_calls.values():
                yield self.format_chunk({"chunk_type": "content_start", "data_type": "tool", "data": tool_deltas[0]})

                for tool_delta in tool_deltas:
                    yield self.format_chunk({"chunk_type": "content_delta", "data_type": "tool", "data": tool_delta})

                yield self.format_chunk({"chunk_type": "content_stop", "data_type": "tool"})

            yield self.format_chunk({"chunk_type": "message_stop", "data": finish_reason or "end_turn"})

            # Skip remaining events as we don't have use for anything except the final usage payload
            async for event in response:
                _ = event

            if event and hasattr(event, "usage") and event.usage:
                yield self.format_chunk({"chunk_type": "metadata", "data": event.usage})

        logger.debug("finished streaming response from model")
</original>
<patched>    @override
    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream conversation with the OpenAI model.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Formatted message chunks from the model.

        Raises:
            ContextWindowOverflowException: If the input exceeds the model's context window.
            ModelThrottledException: If the request is throttled by OpenAI (rate limits).
        """
        BEDROCK_OVERFLOW_MESSAGES = (
            "Input is too long for requested model",
            "input length and max_tokens exceed context limit",
            "too many total text bytes",
        )

        logger.debug("formatting request")
        request = self.format_request(messages, tool_specs, system_prompt, tool_choice)
        logger.debug("formatted request=<%s>", request)

        logger.debug("invoking model")

        # We initialize an OpenAI context on every request so as to avoid connection sharing in the underlying httpx
        # client. The asyncio event loop does not allow connections to be shared. For more details, please refer to
        # https://github.com/encode/httpx/discussions/2959.
        async with self._get_client() as client:
            try:
                response = await client.chat.completions.create(**request)
            except openai.BadRequestError as e:
                # Check if this is a context length exceeded error
                if hasattr(e, "code") and e.code == "context_length_exceeded":
                    logger.warning("OpenAI threw context window overflow error")
                    raise ContextWindowOverflowException(str(e)) from e
                # Re-raise other BadRequestError exceptions
                raise
            except openai.APIError as e:
                # Check for Bedrock-style context overflow errors in generic APIError messages
                if any(msg in str(e) for msg in BEDROCK_OVERFLOW_MESSAGES):
                    logger.warning("Bedrock-style context window overflow detected in APIError")
                    raise ContextWindowOverflowException(str(e)) from e
                raise
            except openai.RateLimitError as e:
                # All rate limit errors should be treated as throttling, not context overflow
                # Rate limits (including TPM) require waiting/retrying, not context reduction
                logger.warning("OpenAI threw rate limit error")
                raise ModelThrottledException(str(e)) from e

            logger.debug("got response from model")
            yield self.format_chunk({"chunk_type": "message_start"})
            tool_calls: dict[int, list[Any]] = {}
            data_type = None
            finish_reason = None  # Store finish_reason for later use
            event = None  # Initialize for scope safety

            async for event in response:
                # Defensive: skip events with empty or missing choices
                if not getattr(event, "choices", None):
                    continue
                choice = event.choices[0]

                if hasattr(choice.delta, "reasoning_content") and choice.delta.reasoning_content:
                    chunks, data_type = self._stream_switch_content("reasoning_content", data_type)
                    for chunk in chunks:
                        yield chunk
                    yield self.format_chunk(
                        {
                            "chunk_type": "content_delta",
                            "data_type": data_type,
                            "data": choice.delta.reasoning_content,
                        }
                    )

                if choice.delta.content:
                    chunks, data_type = self._stream_switch_content("text", data_type)
                    for chunk in chunks:
                        yield chunk
                    yield self.format_chunk(
                        {"chunk_type": "content_delta", "data_type": data_type, "data": choice.delta.content}
                    )

                for tool_call in choice.delta.tool_calls or []:
                    tool_calls.setdefault(tool_call.index, []).append(tool_call)

                if choice.finish_reason:
                    finish_reason = choice.finish_reason  # Store for use outside loop
                    if data_type:
                        yield self.format_chunk({"chunk_type": "content_stop", "data_type": data_type})
                    break

            for tool_deltas in tool_calls.values():
                yield self.format_chunk({"chunk_type": "content_start", "data_type": "tool", "data": tool_deltas[0]})

                for tool_delta in tool_deltas:
                    yield self.format_chunk({"chunk_type": "content_delta", "data_type": "tool", "data": tool_delta})

                yield self.format_chunk({"chunk_type": "content_stop", "data_type": "tool"})

            yield self.format_chunk({"chunk_type": "message_stop", "data": finish_reason or "end_turn"})

            # Skip remaining events as we don't have use for anything except the final usage payload
            async for event in response:
                _ = event

            if event and hasattr(event, "usage") and event.usage:
                yield self.format_chunk({"chunk_type": "metadata", "data": event.usage})

        logger.debug("finished streaming response from model")
</patched>
```

# modification 3
```
<file>src/strands/models/openai.py</file>
<original>    @override
    async def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Get structured output from the model.

        Args:
            output_model: The output model to use for the agent.
            prompt: The prompt messages to use for the agent.
            system_prompt: System prompt to provide context to the model.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Model events with the last being the structured output.

        Raises:
            ContextWindowOverflowException: If the input exceeds the model's context window.
            ModelThrottledException: If the request is throttled by OpenAI (rate limits).
        """
        # We initialize an OpenAI context on every request so as to avoid connection sharing in the underlying httpx
        # client. The asyncio event loop does not allow connections to be shared. For more details, please refer to
        # https://github.com/encode/httpx/discussions/2959.
        async with self._get_client() as client:
            try:
                response: ParsedChatCompletion = await client.beta.chat.completions.parse(
                    model=self.get_config()["model_id"],
                    messages=self.format_request(prompt, system_prompt=system_prompt)["messages"],
                    response_format=output_model,
                )
            except openai.BadRequestError as e:
                # Check if this is a context length exceeded error
                if hasattr(e, "code") and e.code == "context_length_exceeded":
                    logger.warning("OpenAI threw context window overflow error")
                    raise ContextWindowOverflowException(str(e)) from e
                # Re-raise other BadRequestError exceptions
                raise
            except openai.RateLimitError as e:
                # All rate limit errors should be treated as throttling, not context overflow
                # Rate limits (including TPM) require waiting/retrying, not context reduction
                logger.warning("OpenAI threw rate limit error")
                raise ModelThrottledException(str(e)) from e

        parsed: T | None = None
        # Find the first choice with tool_calls
        if len(response.choices) > 1:
            raise ValueError("Multiple choices found in the OpenAI response.")

        for choice in response.choices:
            if isinstance(choice.message.parsed, output_model):
                parsed = choice.message.parsed
                break

        if parsed:
            yield {"output": parsed}
        else:
            raise ValueError("No valid tool use or tool use input was found in the OpenAI response.")
</original>
<patched>    @override
    async def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Get structured output from the model.

        Args:
            output_model: The output model to use for the agent.
            prompt: The prompt messages to use for the agent.
            system_prompt: System prompt to provide context to the model.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Model events with the last being the structured output.

        Raises:
            ContextWindowOverflowException: If the input exceeds the model's context window.
            ModelThrottledException: If the request is throttled by OpenAI (rate limits).
        """
        BEDROCK_OVERFLOW_MESSAGES = (
            "Input is too long for requested model",
            "input length and max_tokens exceed context limit",
            "too many total text bytes",
        )

        # We initialize an OpenAI context on every request so as to avoid connection sharing in the underlying httpx
        # client. The asyncio event loop does not allow connections to be shared. For more details, please refer to
        # https://github.com/encode/httpx/discussions/2959.
        async with self._get_client() as client:
            try:
                response: ParsedChatCompletion = await client.beta.chat.completions.parse(
                    model=self.get_config()["model_id"],
                    messages=self.format_request(prompt, system_prompt=system_prompt)["messages"],
                    response_format=output_model,
                )
            except openai.BadRequestError as e:
                # Check if this is a context length exceeded error
                if hasattr(e, "code") and e.code == "context_length_exceeded":
                    logger.warning("OpenAI threw context window overflow error")
                    raise ContextWindowOverflowException(str(e)) from e
                # Re-raise other BadRequestError exceptions
                raise
            except openai.APIError as e:
                # Check for Bedrock-style context overflow errors in generic APIError messages
                if any(msg in str(e) for msg in BEDROCK_OVERFLOW_MESSAGES):
                    logger.warning("Bedrock-style context window overflow detected in APIError")
                    raise ContextWindowOverflowException(str(e)) from e
                raise
            except openai.RateLimitError as e:
                # All rate limit errors should be treated as throttling, not context overflow
                # Rate limits (including TPM) require waiting/retrying, not context reduction
                logger.warning("OpenAI threw rate limit error")
                raise ModelThrottledException(str(e)) from e

        parsed: T | None = None
        # Find the first choice with tool_calls
        if len(response.choices) > 1:
            raise ValueError("Multiple choices found in the OpenAI response.")

        for choice in response.choices:
            if isinstance(choice.message.parsed, output_model):
                parsed = choice.message.parsed
                break

        if parsed:
            yield {"output": parsed}
        else:
            raise ValueError("No valid tool use or tool use input was found in the OpenAI response.")
</patched>
```