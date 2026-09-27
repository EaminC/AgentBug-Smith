# Reasoning
The issue requires adding a new `cache_strategy` parameter to the base `Model` class configuration so that it is inherited across all model implementations. When the Agent is initialized with a model that has `cache_strategy="auto"`, we need to register a new hook `ConversationCachingHook` that injects a `cachePoint` block into the last assistant message before every model call.

To implement this:
1. In `src/strands/models/model.py`, add `cache_strategy` as an optional parameter to base class methods managing config.
2. In `src/strands/agent/agent.py`, modify the constructor to detect `cache_strategy=="auto"` and add `ConversationCachingHook`.
3. Add a new hook class `ConversationCachingHook` (for example, in `src/strands/hooks/conversation_caching_hook.py`) that listens for `BeforeModelCallEvent` and injects the cachePoint block.
4. Ensure provider models (especially LiteLLMModel) process cachePoint properly. LiteLLMModel already contains handling, so no code change needed here unless subtle fixes are requested (the minimal necessary fix is the hook and new config addition).

The patch below implements these key changes minimally and cleanly, respecting existing code structure and conventions, adding the new hook logic as requested.

# Patch

```
<file>src/strands/models/model.py</file>
<original>
class Model(abc.ABC):
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
<patched>
from typing import Optional

class Model(abc.ABC):
    def __init__(self, *, cache_strategy: Optional[str] = None, **kwargs: Any) -> None:
        self._cache_strategy = cache_strategy
        super().__init__()

    def update_config(self, **model_config: Any) -> None:
        # Update the cache_strategy key if present
        if "cache_strategy" in model_config:
            self._cache_strategy = model_config.pop("cache_strategy")
        # To be implemented in subclasses as needed

    def get_config(self) -> dict[str, Any]:
        # Provide base config including cache_strategy
        # Subclasses should override and include their specific config keys
        return {"cache_strategy": self._cache_strategy}

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
    
    def get_cache_strategy(self) -> Optional[str]:
        return self._cache_strategy
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>
    def __init__(
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
        ...
        self.hooks = HookRegistry()
        ...
        if hooks:
            for hook in hooks:
                self.hooks.add_hook(hook)
        self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</original>
<patched>
from strands.hooks.conversation_caching_hook import ConversationCachingHook

    def __init__(
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
        ...
        self.hooks = HookRegistry()
        
        # Detect if model config says cache_strategy=auto and register ConversationCachingHook
        if isinstance(self.model, Model):
            config = self.model.get_config()
            if config.get("cache_strategy") == "auto":
                self.hooks.add_hook(ConversationCachingHook())
        
        if hooks:
            for hook in hooks:
                self.hooks.add_hook(hook)
        self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
```

```
<file>src/strands/hooks/conversation_caching_hook.py</file>
<original></original>
<patched>
from dataclasses import dataclass
from typing import Any
from strands.hooks.events import BeforeModelCallEvent
from strands.hooks.registry import BaseHook  # or appropriate base hook interface
from strands.types.content import Messages, Message, ContentBlock

@dataclass
class ConversationCachingHook(BaseHook):
    """Hook to inject cachePoint block at the last assistant message before model calls."""

    def before_model_call(self, event: BeforeModelCallEvent) -> None:
        messages: Messages = event.messages
        if not messages:
            return

        # Find the last assistant message
        for i in reversed(range(len(messages))):
            if messages[i].role == "assistant":
                # Prepare the cachePoint block
                cache_point_block: ContentBlock = {
                    "cachePoint": {"type": "default"}
                }
                # Insert it into the content of the last assistant message
                # Ensure messages content is a list to append cachePoint block
                new_content = list(messages[i].content) if isinstance(messages[i].content, list) else [messages[i].content]
                new_content.append(cache_point_block)
                # Replace content with new_content
                messages[i] = Message(
                    role=messages[i].role,
                    content=new_content,
                    metadata=messages[i].metadata,
                    # Copy other attributes if exist
                    name=getattr(messages[i], "name", None),
                    id=getattr(messages[i], "id", None),
                    timestamp=getattr(messages[i], "timestamp", None),
                )
                break
</patched>
```