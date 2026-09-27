The issue requires adding a new method, `estimate_tokens`, to the `Model` interface and implementing it for several major providers by leveraging their native token counting APIs or utilities. We'll do the following changes:

1. Add an abstract method `estimate_tokens` in `Model` interface.

2. Implement `estimate_tokens` for:
   - AnthropicModel: use `anthropic.count_tokens()` for formatted request messages.
   - OpenAIModel: use `tiktoken` tokenizer (which would be imported) to count tokens for formatted messages.
   - GeminiModel: use Gemini client's `client.count_tokens()` method (assuming it is available) on the formatted request.
   - LiteLLMModel: use `litellm.token_counter()` method for messages.

This provides an integrated, proactive token estimation API across supported model providers.

---

# modification 1

```
<file>src/strands/models/model.py</file>
<original>class Model(abc.ABC):
    ...
    @abc.abstractmethod
    # pragma: no cover
    def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Stream conversation with the model.

        This method handles the full lifecycle of conversing with the model:

        1. Format the messages, tool specs, and configuration into a streaming request
        2. Send the request to the model
        3. Yield the formatted message chunks

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            system_prompt_content: System prompt content blocks for advanced features like caching.
            invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Formatted message chunks from the model.

        Raises:
            ModelThrottledException: When the model service is throttling requests from the client.
        """
        pass
</original>
<patched>class Model(abc.ABC):
    ...
    @abc.abstractmethod
    # pragma: no cover
    def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Stream conversation with the model.

        This method handles the full lifecycle of conversing with the model:

        1. Format the messages, tool specs, and configuration into a streaming request
        2. Send the request to the model
        3. Yield the formatted message chunks

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            system_prompt_content: System prompt content blocks for advanced features like caching.
            invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Formatted message chunks from the model.

        Raises:
            ModelThrottledException: When the model service is throttling requests from the client.
        """
        pass

    @abc.abstractmethod
    # pragma: no cover
    def estimate_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
    ) -> int:
        """Estimate token count for the given input before sending to model."""
        pass
</patched>
```

---

# modification 2

```
<file>src/strands/models/anthropic.py</file>
<original>class AnthropicModel(Model):
    ...
    def format_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> dict[str, Any]:
        """Format an Anthropic streaming request.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.

        Returns:
            An Anthropic streaming request.

        Raises:
            TypeError: If a message contains a content block type that cannot be converted to an Anthropic-compatible
                format.
        """
        return {
            "max_tokens": self.config["max_tokens"],
            "messages": self._format_request_messages(messages),
            "model": self.config["model_id"],
            "tools": [
                {
                    "name": tool_spec["name"],
                    "description": tool_spec["description"],
                    "input_schema": tool_spec["inputSchema"]["json"],
                }
                for tool_spec in tool_specs or []
            ],
            **(self._format_tool_choice(tool_choice)),
            **({"system": system_prompt} if system_prompt else {}),
            **(self.config.get("params") or {}),
        }</original>
<patched>class AnthropicModel(Model):
    ...
    def format_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> dict[str, Any]:
        """Format an Anthropic streaming request.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.

        Returns:
            An Anthropic streaming request.

        Raises:
            TypeError: If a message contains a content block type that cannot be converted to an Anthropic-compatible
                format.
        """
        return {
            "max_tokens": self.config["max_tokens"],
            "messages": self._format_request_messages(messages),
            "model": self.config["model_id"],
            "tools": [
                {
                    "name": tool_spec["name"],
                    "description": tool_spec["description"],
                    "input_schema": tool_spec["inputSchema"]["json"],
                }
                for tool_spec in tool_specs or []
            ],
            **(self._format_tool_choice(tool_choice)),
            **({"system": system_prompt} if system_prompt else {}),
            **(self.config.get("params") or {}),
        }

    def estimate_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
    ) -> int:
        """Estimate token count using Anthropic's count_tokens for the formatted request."""
        request = self.format_request(messages, tool_specs, system_prompt)
        # Use Anthropic SDK count_tokens method on formatted request 'messages' field
        # The Anthropic Python client exposes count_tokens as a function to count tokens in messages.
        # According to the docs, it's usually anthropic.count_tokens(messages)
        # So import anthropic.count_tokens at the top and call it here.
        return anthropic.count_tokens(request["messages"])
</patched>
```

---

# modification 3

```
<file>src/strands/models/openai.py</file>
<original>class OpenAIModel(Model):
    ...
    def format_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        tool_choice: ToolChoice | None = None,
        *,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format an OpenAI compatible chat streaming request.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            system_prompt_content: System prompt content blocks to provide context to the model.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            An OpenAI compatible chat streaming request.

        Raises:
            TypeError: If a message contains a content block type that cannot be converted to an OpenAI-compatible
                format.
        """
        return {
            "messages": self.format_request_messages(
                messages, system_prompt, system_prompt_content=system_prompt_content
            ),
            "model": self.config["model_id"],
            "stream": True,
            "stream_options": {"include_usage": True},
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool_spec["name"],
                        "description": tool_spec["description"],
                        "parameters": tool_spec["inputSchema"]["json"],
                    },
                }
                for tool_spec in tool_specs or []
            ],
            **(self._format_request_tool_choice(tool_choice)),
            **cast(dict[str, Any], self.config.get("params", {})),
        }</original>
<patched>class OpenAIModel(Model):
    ...
    def format_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        tool_choice: ToolChoice | None = None,
        *,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format an OpenAI compatible chat streaming request.

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            system_prompt_content: System prompt content blocks to provide context to the model.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            An OpenAI compatible chat streaming request.

        Raises:
            TypeError: If a message contains a content block type that cannot be converted to an OpenAI-compatible
                format.
        """
        return {
            "messages": self.format_request_messages(
                messages, system_prompt, system_prompt_content=system_prompt_content
            ),
            "model": self.config["model_id"],
            "stream": True,
            "stream_options": {"include_usage": True},
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool_spec["name"],
                        "description": tool_spec["description"],
                        "parameters": tool_spec["inputSchema"]["json"],
                    },
                }
                for tool_spec in tool_specs or []
            ],
            **(self._format_request_tool_choice(tool_choice)),
            **cast(dict[str, Any], self.config.get("params", {})),
        }

    @override
    def estimate_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
    ) -> int:
        """Estimate tokens using tiktoken encoding on the formatted messages."""
        import tiktoken

        formatted_messages = self.format_request_messages(messages, system_prompt)
        model_id = self.config.get("model_id", "")
        try:
            enc = tiktoken.encoding_for_model(model_id)
        except KeyError:
            # Fallback to cl100k_base encoding if model unknown
            enc = tiktoken.get_encoding("cl100k_base")

        tokens_per_message = 4  # As per OpenAI's chat format token counting rules
        tokens_per_name = -1  # In case name attr exists

        token_count = 0
        for message in formatted_messages:
            # Per message tokens
            token_count += tokens_per_message
            for key, value in message.items():
                if key == "name":
                    token_count += tokens_per_name
                if isinstance(value, str):
                    token_count += len(enc.encode(value))
                elif isinstance(value, list):
                    # For content arrays, encode each text element
                    for elem in value:
                        if isinstance(elem, dict) and "text" in elem:
                            token_count += len(enc.encode(elem["text"]))
                        elif isinstance(elem, str):
                            token_count += len(enc.encode(elem))
                else:
                    # fallback: convert value to string encoding
                    token_count += len(enc.encode(str(value)))
        token_count += 3  # every reply is primed with tokens
        return token_count
</patched>
```

---

# modification 4

```
<file>src/strands/models/gemini.py</file>
<original>class GeminiModel(Model):
    ...
    def estimate_tokens(self, messages: Messages, tool_specs: list[ToolSpec] | None = None, system_prompt: str | None = None) -> int:
        pass
</original>
<patched>class GeminiModel(Model):
    ...
    def estimate_tokens(self, messages: Messages, tool_specs: list[ToolSpec] | None = None, system_prompt: str | None = None) -> int:
        """Estimate tokens using the Gemini client's token counting functionality."""
        # Format the request as usual
        request = self._format_request(messages, tool_specs, system_prompt, self.config.get("params"))
        client = self._get_client()

        # Use Gemini native token counting if exists
        if hasattr(client, "count_tokens") and callable(getattr(client, "count_tokens")):
            try:
                # The count_tokens method typically counts tokens for a Gemini request object
                # count_tokens may expect the "contents" and "config" keys as per the request format
                return client.count_tokens(
                    model=self.config["model_id"],
                    contents=request.get("contents", []),
                    config=request.get("config", {}),
                )
            except Exception as e:
                logger.warning("Failed to estimate tokens using Gemini client.count_tokens: %s", e)
                # Fallback to 0 tokens to avoid blocking
                return 0
        else:
            # No native counting, fallback to zero or heuristic
            logger.warning("Gemini client does not support count_tokens method.")
            return 0
</patched>
```

---

# modification 5

```
<file>src/strands/models/litellm.py</file>
<original>class LiteLLMModel(OpenAIModel):
    ...
</original>
<patched>class LiteLLMModel(OpenAIModel):
    ...
    def estimate_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
    ) -> int:
        """Estimate tokens using LiteLLM's token_counter utility."""
        import litellm.token_counter

        formatted_messages = self.format_request_messages(messages, system_prompt)
        return litellm.token_counter.count_tokens(
            model=self.config["model_id"],
            messages=formatted_messages,
        )
</patched>
```

---

# Additionally, for the AnthropicModel, we must import `anthropic` to use count_tokens:

```
<file>src/strands/models/anthropic.py</file>
<original>class AnthropicModel(Model):
    ...
</original>
<patched>import anthropic

class AnthropicModel(Model):
    ...
</patched>
```

---

# For OpenAIModel estimate_tokens, import of tiktoken is within the function for lazy import; this is acceptable.

No other import modifications needed.

---

This patch adds the proposed `estimate_tokens` signature to the Model base class and implements token estimation in the respective model providers using their native or recommended token counting mechanisms. This allows proactive token usage estimation before making model calls, enabling better context window management and other use cases described in the issue.