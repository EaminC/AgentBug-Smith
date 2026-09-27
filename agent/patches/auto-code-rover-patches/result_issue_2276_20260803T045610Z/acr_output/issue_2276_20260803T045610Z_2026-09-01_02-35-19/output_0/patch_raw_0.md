The issue is that the current LLM class tightly couples to litellm.completion for making calls, which requires an API key based authentication. The user wants to have custom LLM clients (e.g., Enterprise LLM Gateway) that might use JWT authentication or completely different mechanisms without relying on litellm. So the solution is to extend the LLM class to support a pluggable "client" attribute or function which, if provided, will be called instead of litellm.completion, allowing the user to supply their own client implementation with custom authentication/token management.

To do this:
- Add an optional `client` attribute to the LLM constructor, allowing the user to inject their own client callable.
- Modify the `_handle_streaming_response` and `_handle_non_streaming_response` to conditionally call the `client` callable if set, otherwise fallback to the existing litellm.completion call.
- This keeps backward compatibility for existing users relying on litellm.
- This also matches the requested feature of a structure similar to langchain_core.language_models.chat_models.BaseChatModel, i.e., pluggable call implementations.
- It also allows users to override the `call` method to bypass litellm completely if needed.

No other changes are really needed.

---

# modification 1

```
<file>src/crewai/llm.py</file>
<original>class LLM:
    def __init__(
        self,
        model: str,
        timeout: Optional[Union[float, int]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        n: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        max_completion_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[Dict[int, float]] = None,
        response_format: Optional[Type[BaseModel]] = None,
        seed: Optional[int] = None,
        logprobs: Optional[int] = None,
        top_logprobs: Optional[int] = None,
        base_url: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
        callbacks: List[Any] = [],
        reasoning_effort: Optional[Literal["none", "low", "medium", "high"]] = None,
        stream: bool = False,
        **kwargs,
    ):
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.n = n
        self.max_completion_tokens = max_completion_tokens
        self.max_tokens = max_tokens
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.logit_bias = logit_bias
        self.response_format = response_format
        self.seed = seed
        self.logprobs = logprobs
        self.top_logprobs = top_logprobs
        self.base_url = base_url
        self.api_base = api_base
        self.api_version = api_version
        self.api_key = api_key
        self.callbacks = callbacks
        self.context_window_size = 0
        self.reasoning_effort = reasoning_effort
        self.additional_params = kwargs
        self.is_anthropic = self._is_anthropic_model(model)
        self.stream = stream

        litellm.drop_params = True

        # Normalize self.stop to always be a List[str]
        if stop is None:
            self.stop: List[str] = []
        elif isinstance(stop, str):
            self.stop = [stop]
        else:
            self.stop = stop

        self.set_callbacks(callbacks)
        self.set_env_callbacks()
</original>
<patched>class LLM:
    def __init__(
        self,
        model: str,
        timeout: Optional[Union[float, int]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        n: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        max_completion_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[Dict[int, float]] = None,
        response_format: Optional[Type[BaseModel]] = None,
        seed: Optional[int] = None,
        logprobs: Optional[int] = None,
        top_logprobs: Optional[int] = None,
        base_url: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
        callbacks: List[Any] = [],
        reasoning_effort: Optional[Literal["none", "low", "medium", "high"]] = None,
        stream: bool = False,
        client: Optional[Callable[..., Any]] = None,
        **kwargs,
    ):
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.n = n
        self.max_completion_tokens = max_completion_tokens
        self.max_tokens = max_tokens
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.logit_bias = logit_bias
        self.response_format = response_format
        self.seed = seed
        self.logprobs = logprobs
        self.top_logprobs = top_logprobs
        self.base_url = base_url
        self.api_base = api_base
        self.api_version = api_version
        self.api_key = api_key
        self.callbacks = callbacks
        self.context_window_size = 0
        self.reasoning_effort = reasoning_effort
        self.additional_params = kwargs
        self.is_anthropic = self._is_anthropic_model(model)
        self.stream = stream
        self.client = client

        litellm.drop_params = True

        # Normalize self.stop to always be a List[str]
        if stop is None:
            self.stop: List[str] = []
        elif isinstance(stop, str):
            self.stop = [stop]
        else:
            self.stop = stop

        self.set_callbacks(callbacks)
        self.set_env_callbacks()
</patched>
```

# modification 2

```
<file>src/crewai/llm.py</file>
<original>    def _handle_streaming_response(
        self,
        params: Dict[str, Any],
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Handle a streaming response from the LLM.

        Args:
            params: Parameters for the completion call
            callbacks: Optional list of callback functions
            available_functions: Dict of available functions

        Returns:
            str: The complete response text

        Raises:
            Exception: If no content is received from the streaming response
        """
        # --- 1) Initialize response tracking
        full_response = ""
        last_chunk = None
        chunk_count = 0
        usage_info = None

        # --- 2) Make sure stream is set to True and include usage metrics
        params["stream"] = True
        params["stream_options"] = {"include_usage": True}

        try:
            # --- 3) Process each chunk in the stream
            for chunk in litellm.completion(**params):
                chunk_count += 1
                last_chunk = chunk

                # Extract content from the chunk
                chunk_content = None

                # Safely extract content from various chunk formats
                try:
                    # Try to access choices safely
                    choices = None
                    if isinstance(chunk, dict) and "choices" in chunk:
                        choices = chunk["choices"]
                    elif hasattr(chunk, "choices"):
                        # Check if choices is not a type but an actual attribute with value
                        if not isinstance(getattr(chunk, "choices"), type):
                            choices = getattr(chunk, "choices")

                    # Try to extract usage information if available
                    if isinstance(chunk, dict) and "usage" in chunk:
                        usage_info = chunk["usage"]
                    elif hasattr(chunk, "usage"):
                        # Check if usage is not a type but an actual attribute with value
                        if not isinstance(getattr(chunk, "usage"), type):
                            usage_info = getattr(chunk, "usage")

                    if choices and len(choices) > 0:
                        choice = choices[0]

                        # Handle different delta formats
                        delta = None
                        if isinstance(choice, dict) and "delta" in choice:
                            delta = choice["delta"]
                        elif hasattr(choice, "delta"):
                            delta = getattr(choice, "delta")

                        # Extract content from delta
                        if delta:
                            # Handle dict format
                            if isinstance(delta, dict):
                                if "content" in delta and delta["content"] is not None:
                                    chunk_content = delta["content"]
                            # Handle object format
                            elif hasattr(delta, "content"):
                                chunk_content = getattr(delta, "content")

                            # Handle case where content might be None or empty
                            if chunk_content is None and isinstance(delta, dict):
                                # Some models might send empty content chunks
                                chunk_content = ""
                except Exception as e:
                    logging.debug(f"Error extracting content from chunk: {e}")
                    logging.debug(f"Chunk format: {type(chunk)}, content: {chunk}")

                # Only add non-None content to the response
                if chunk_content is not None:
                    # Add the chunk content to the full response
                    full_response += chunk_content

                    # Emit the chunk event
                    crewai_event_bus.emit(
                        self,
                        event=LLMStreamChunkEvent(chunk=chunk_content),
                    )

            # --- 4) Fallback to non-streaming if no content received
            if not full_response.strip() and chunk_count == 0:
                logging.warning(
                    "No chunks received in streaming response, falling back to non-streaming"
                )
                non_streaming_params = params.copy()
                non_streaming_params["stream"] = False
                non_streaming_params.pop(
                    "stream_options", None
                )  # Remove stream_options for non-streaming call
                return self._handle_non_streaming_response(
                    non_streaming_params, callbacks, available_functions
                )

            # --- 5) Handle empty response with chunks
            if not full_response.strip() and chunk_count > 0:
                logging.warning(
                    f"Received {chunk_count} chunks but no content was extracted"
                )
                if last_chunk is not None:
                    try:
                        # Try to extract content from the last chunk's message
                        choices = None
                        if isinstance(last_chunk, dict) and "choices" in last_chunk:
                            choices = last_chunk["choices"]
                        elif hasattr(last_chunk, "choices"):
                            if not isinstance(getattr(last_chunk, "choices"), type):
                                choices = getattr(last_chunk, "choices")

                        if choices and len(choices) > 0:
                            choice = choices[0]

                            # Try to get content from message
                            message = None
                            if isinstance(choice, dict) and "message" in choice:
                                message = choice["message"]
                            elif hasattr(choice, "message"):
                                message = getattr(choice, "message")

                            if message:
                                content = None
                                if isinstance(message, dict) and "content" in message:
                                    content = message["content"]
                                elif hasattr(message, "content"):
                                    content = getattr(message, "content")

                                if content:
                                    full_response = content
                                    logging.info(
                                        f"Extracted content from last chunk message: {full_response}"
                                    )
                    except Exception as e:
                        logging.debug(f"Error extracting content from last chunk: {e}")
                        logging.debug(
                            f"Last chunk format: {type(last_chunk)}, content: {last_chunk}"
                        )

            # --- 6) If still empty, raise an error instead of using a default response
            if not full_response.strip():
                raise Exception(
                    "No content received from streaming response. Received empty chunks or failed to extract content."
                )

            # --- 7) Check for tool calls in the final response
            tool_calls = None
            try:
                if last_chunk:
                    choices = None
                    if isinstance(last_chunk, dict) and "choices" in last_chunk:
                        choices = last_chunk["choices"]
                    elif hasattr(last_chunk, "choices"):
                        if not isinstance(getattr(last_chunk, "choices"), type):
                            choices = getattr(last_chunk, "choices")

                    if choices and len(choices) > 0:
                        choice = choices[0]

                        message = None
                        if isinstance(choice, dict) and "message" in choice:
                            message = choice["message"]
                        elif hasattr(choice, "message"):
                            message = getattr(choice, "message")

                        if message:
                            if isinstance(message, dict) and "tool_calls" in message:
                                tool_calls = message["tool_calls"]
                            elif hasattr(message, "tool_calls"):
                                tool_calls = getattr(message, "tool_calls")
            except Exception as e:
                logging.debug(f"Error checking for tool calls: {e}")

            # --- 8) If no tool calls or no available functions, return the text response directly
            if not tool_calls or not available_functions:
                # Log token usage if available in streaming mode
                self._handle_streaming_callbacks(callbacks, usage_info, last_chunk)
                # Emit completion event and return response
                self._handle_emit_call_events(full_response, LLMCallType.LLM_CALL)
                return full_response

            # --- 9) Handle tool calls if present
            tool_result = self._handle_tool_call(tool_calls, available_functions)
            if tool_result is not None:
                return tool_result

            # --- 10) Log token usage if available in streaming mode
            self._handle_streaming_callbacks(callbacks, usage_info, last_chunk)

            # --- 11) Emit completion event and return response
            self._handle_emit_call_events(full_response, LLMCallType.LLM_CALL)
            return full_response

        except Exception as e:
            logging.error(f"Error in streaming response: {str(e)}")
            if full_response.strip():
                logging.warning(f"Returning partial response despite error: {str(e)}")
                self._handle_emit_call_events(full_response, LLMCallType.LLM_CALL)
                return full_response

            # Emit failed event and re-raise the exception
            crewai_event_bus.emit(
                self,
                event=LLMCallFailedEvent(error=str(e)),
            )
            raise Exception(f"Failed to get streaming response: {str(e)}")</original>
<patched>    def _handle_streaming_response(
        self,
        params: Dict[str, Any],
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Handle a streaming response from the LLM.

        Args:
            params: Parameters for the completion call
            callbacks: Optional list of callback functions
            available_functions: Dict of available functions

        Returns:
            str: The complete response text

        Raises:
            Exception: If no content is received from the streaming response
        """
        # --- 1) Initialize response tracking
        full_response = ""
        last_chunk = None
        chunk_count = 0
        usage_info = None

        # --- 2) Make sure stream is set to True and include usage metrics
        params["stream"] = True
        params["stream_options"] = {"include_usage": True}

        try:
            # --- 3) Process each chunk in the stream
            # Use custom client if provided, else fall back to litellm.completion
            client_callable = self.client or litellm.completion
            for chunk in client_callable(**params):
                chunk_count += 1
                last_chunk = chunk

                # Extract content from the chunk
                chunk_content = None

                # Safely extract content from various chunk formats
                try:
                    # Try to access choices safely
                    choices = None
                    if isinstance(chunk, dict) and "choices" in chunk:
                        choices = chunk["choices"]
                    elif hasattr(chunk, "choices"):
                        # Check if choices is not a type but an actual attribute with value
                        if not isinstance(getattr(chunk, "choices"), type):
                            choices = getattr(chunk, "choices")

                    # Try to extract usage information if available
                    if isinstance(chunk, dict) and "usage" in chunk:
                        usage_info = chunk["usage"]
                    elif hasattr(chunk, "usage"):
                        # Check if usage is not a type but an actual attribute with value
                        if not isinstance(getattr(chunk, "usage"), type):
                            usage_info = getattr(chunk, "usage")

                    if choices and len(choices) > 0:
                        choice = choices[0]

                        # Handle different delta formats
                        delta = None
                        if isinstance(choice, dict) and "delta" in choice:
                            delta = choice["delta"]
                        elif hasattr(choice, "delta"):
                            delta = getattr(choice, "delta")

                        # Extract content from delta
                        if delta:
                            # Handle dict format
                            if isinstance(delta, dict):
                                if "content" in delta and delta["content"] is not None:
                                    chunk_content = delta["content"]
                            # Handle object format
                            elif hasattr(delta, "content"):
                                chunk_content = getattr(delta, "content")

                            # Handle case where content might be None or empty
                            if chunk_content is None and isinstance(delta, dict):
                                # Some models might send empty content chunks
                                chunk_content = ""
                except Exception as e:
                    logging.debug(f"Error extracting content from chunk: {e}")
                    logging.debug(f"Chunk format: {type(chunk)}, content: {chunk}")

                # Only add non-None content to the response
                if chunk_content is not None:
                    # Add the chunk content to the full response
                    full_response += chunk_content

                    # Emit the chunk event
                    crewai_event_bus.emit(
                        self,
                        event=LLMStreamChunkEvent(chunk=chunk_content),
                    )

            # --- 4) Fallback to non-streaming if no content received
            if not full_response.strip() and chunk_count == 0:
                logging.warning(
                    "No chunks received in streaming response, falling back to non-streaming"
                )
                non_streaming_params = params.copy()
                non_streaming_params["stream"] = False
                non_streaming_params.pop(
                    "stream_options", None
                )  # Remove stream_options for non-streaming call
                return self._handle_non_streaming_response(
                    non_streaming_params, callbacks, available_functions
                )

            # --- 5) Handle empty response with chunks
            if not full_response.strip() and chunk_count > 0:
                logging.warning(
                    f"Received {chunk_count} chunks but no content was extracted"
                )
                if last_chunk is not None:
                    try:
                        # Try to extract content from the last chunk's message
