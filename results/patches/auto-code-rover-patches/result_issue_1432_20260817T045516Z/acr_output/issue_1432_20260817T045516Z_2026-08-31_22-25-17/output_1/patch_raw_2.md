```
<file>src/strands/models/model.py</file>
<original>class Model(abc.ABC):
    @abc.abstractmethod
    def update_config(self, **model_config: Any) -> None:
    @abc.abstractmethod
    def get_config(self) -> Any:
    @abc.abstractmethod
    def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, T | Any], None]:
    @abc.abstractmethod
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
</original>
<patched>from typing import Optional

class Model(abc.ABC):
    cache_strategy: Optional[str] = None  # Add cache_strategy attribute to base class

    @abc.abstractmethod
    def update_config(self, **model_config: Any) -> None:
        if "cache_strategy" in model_config:
            self.cache_strategy = model_config.pop("cache_strategy")
        # original implementation may follow or be abstract

    @abc.abstractmethod
    def get_config(self) -> Any:
        # In implementations this should include cache_strategy in returned config
        # This is left abstract here but subclasses should include cache_strategy in Config data
        ...

    @abc.abstractmethod
    def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        ...

    @abc.abstractmethod
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
        ...
</patched>
</file>

<file>src/strands/agent/agent.py</file>
<original>    def __init__(
        self,
        model: Model | str | None = None,
        messages: Messages | None = None,
        tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,
        callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,
        trace_attributes: Mapping[str, AttributeValue] | None = None,
        *,
        agent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: AgentState | dict | None = None,
        hooks: list[HookProvider] | None = None,
        session_manager: SessionManager | None = None,
        tool_executor: ToolExecutor | None = None,
        retry_strategy: ModelRetryStrategy | None = None,
    ):</original>
<patched>    def __init__(
        self,
        model: Model | str | None = None,
        messages: Messages | None = None,
        tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,
        callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,
        trace_attributes: Mapping[str, AttributeValue] | None = None,
        *,
        agent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: AgentState | dict | None = None,
        hooks: list[HookProvider] | None = None,
        session_manager: SessionManager | None = None,
        tool_executor: ToolExecutor | None = None,
        retry_strategy: ModelRetryStrategy | None = None,
    ):
        """Initialize the Agent with the specified configuration.
        ...
        """
        self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
        self.messages = messages if messages is not None else []
        # initializing self._system_prompt for backwards compatibility
        self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
        self._default_structured_output_model = structured_output_model
        self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
        self.name = name or _DEFAULT_AGENT_NAME
        self.description = description

        # If not provided, create a new PrintingCallbackHandler instance
        # If explicitly set to None, use null_callback_handler
        # Otherwise use the passed callback_handler
        self.callback_handler: Callable[..., Any] | PrintingCallbackHandler
        if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
            self.callback_handler = PrintingCallbackHandler()
        elif callback_handler is None:
            self.callback_handler = null_callback_handler
        else:
            self.callback_handler = callback_handler

        self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()

        # Process trace attributes to ensure they're of compatible types
        self.trace_attributes: dict[str, AttributeValue] = {}
        if trace_attributes:
            for k, v in trace_attributes.items():
                if isinstance(v, (str, int, float, bool)) or (
                    isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
                ):
                    self.trace_attributes[k] = v

        self.record_direct_tool_call = record_direct_tool_call
        self.load_tools_from_directory = load_tools_from_directory

        self.tool_registry = ToolRegistry()

        # Process tool list if provided
        if tools is not None:
            self.tool_registry.process_tools(tools)

        # Initialize tools and configuration
        self.tool_registry.initialize_tools(self.load_tools_from_directory)
        if load_tools_from_directory:
            self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)

        self.event_loop_metrics = EventLoopMetrics()

        # Initialize tracer instance (no-op if not configured)
        self.tracer = get_tracer()
        self.trace_span: trace_api.Span | None = None

        # Initialize agent state management
        if state is not None:
            if isinstance(state, dict):
                self.state = AgentState(state)
            elif isinstance(state, AgentState):
                self.state = state
            else:
                raise ValueError("state must be an AgentState object or a dict")
        else:
            self.state = AgentState()

        self.tool_caller = _ToolCaller(self)

        self.hooks = HookRegistry()

        self._interrupt_state = _InterruptState()

        # Initialize lock for guarding concurrent invocations
        # Using threading.Lock instead of asyncio.Lock because run_async() creates
        # separate event loops in different threads, so asyncio.Lock wouldn't work
        self._invocation_lock = threading.Lock()

        # In the future, we'll have a RetryStrategy base class but until
        # that API is determined we only allow ModelRetryStrategy
        if retry_strategy and type(retry_strategy) is not ModelRetryStrategy:
            raise ValueError("retry_strategy must be an instance of ModelRetryStrategy")

        self._retry_strategy = (
            retry_strategy
            if retry_strategy is not None
            else ModelRetryStrategy(max_attempts=MAX_ATTEMPTS, max_delay=MAX_DELAY, initial_delay=INITIAL_DELAY)
        )

        # Initialize session management functionality
        self._session_manager = session_manager
        if self._session_manager:
            self.hooks.add_hook(self._session_manager)

        # Allow conversation_managers to subscribe to hooks
        self.hooks.add_hook(self.conversation_manager)

        # Register retry strategy as a hook
        self.hooks.add_hook(self._retry_strategy)

        self.tool_executor = tool_executor or ConcurrentToolExecutor()

        if hooks:
            for hook in hooks:
                self.hooks.add_hook(hook)

        # Automatically add ConversationCachingHook if model cache_strategy is "auto"
        model_cache_strategy = None
        if hasattr(self.model, "get_config") and callable(getattr(self.model, "get_config")):
            config = self.model.get_config()
            model_cache_strategy = getattr(config, "cache_strategy", None)
        if model_cache_strategy == "auto":
            from strands.hooks.conversation_caching_hook import ConversationCachingHook
            self.hooks.add_hook(ConversationCachingHook())

        self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
</file>

<file>src/strands/hooks/conversation_caching_hook.py</file>
<original></original>
<patched>from dataclasses import dataclass
from typing import Any, cast

from strands.hooks.events import BeforeModelCallEvent
from strands.hooks.registry import HookProvider
from strands.types.content import Messages, ContentBlock


@dataclass
class ConversationCachingHook(HookProvider):
    def before_model_call(self, event: BeforeModelCallEvent) -> None:
        messages: Messages | None = getattr(event, "messages", None)
        if not messages:
            return

        # Find the last assistant message to inject the cachePoint
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "assistant":
                # Copy content list to avoid potential mutation issues
                content = list(messages[i].content)

                # Append a cachePoint block as required
                cache_point_block: ContentBlock = {"cachePoint": {"type": "default"}}
                content.append(cache_point_block)

                # Replace the content with the updated one
                messages[i] = messages[i]._replace(content=content)  # Assuming Message is a NamedTuple or similar

                break
</patched>
</file>

<file>src/strands/models/litellm.py</file>
<original>    def _format_system_messages(
        cls,
        system_prompt: str | None = None,
        *,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        for block in system_prompt_content or []:
            if "text" in block:
                system_content.append({"type": "text", "text": block["text"]})
            elif "cachePoint" in block and block["cachePoint"].get("type") == "default":
                # Apply cache control to the immediately preceding content block
                # for LiteLLM/Anthropic compatibility
                if system_content:
</original>
<patched>    def _format_system_messages(
        cls,
        system_prompt: str | None = None,
        *,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        system_content = []
        for block in system_prompt_content or []:
            if "text" in block:
                system_content.append({"type": "text", "text": block["text"]})
            elif "cachePoint" in block and block["cachePoint"].get("type") == "default":
                # Apply cache control to the immediately preceding content block
                # for LiteLLM/Anthropic compatibility
                if system_content:
</patched>
</file>
```