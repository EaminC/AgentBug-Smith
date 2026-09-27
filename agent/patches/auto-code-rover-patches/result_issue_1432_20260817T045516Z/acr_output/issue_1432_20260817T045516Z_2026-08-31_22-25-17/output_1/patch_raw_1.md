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
    cache_strategy: Optional[str] = None

    @abc.abstractmethod
    def update_config(self, **model_config: Any) -> None:
        if "cache_strategy" in model_config:
            self.cache_strategy = model_config.pop("cache_strategy")
        # Existing update_config logic may follow

    @abc.abstractmethod
    def get_config(self) -> Any:
        config = self._get_config_internal()
        if self.cache_strategy is not None:
            config.cache_strategy = self.cache_strategy
        return config

    @abc.abstractmethod
    def _get_config_internal(self) -> Any:
        """Helper to get internal config object, to be implemented by subclass."""

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
    ):
        ...
        self.hooks = HookRegistry()
        ...
        if hooks:
            for hook in hooks:
                self.hooks.add_hook(hook)
        self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</original>
<patched>    from strands.hooks.conversation_caching_hook import ConversationCachingHook

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

        # Automatically add ConversationCachingHook if model cache_strategy is "auto"
        if isinstance(self.model, Model):
            config = getattr(self.model, "get_config", lambda: {})()
            cache_strategy = getattr(config, "cache_strategy", None)
            if cache_strategy == "auto":
                self.hooks.add_hook(ConversationCachingHook())

        ...
        if hooks:
            for hook in hooks:
                self.hooks.add_hook(hook)
        self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
</file>

<file>src/strands/hooks/conversation_caching_hook.py</file>
<original>...</original>
<patched>from dataclasses import dataclass
from typing import Any, cast

from strands.hooks.events import BeforeModelCallEvent
from strands.hooks.registry import BaseHookProvider
from strands.types.content import ContentBlock, Messages, Role

@dataclass
class ConversationCachingHook(BaseHookProvider):
    """
    Hook to inject a cachePoint block into the last assistant message on each BeforeModelCallEvent.
    This enables automatic prompt caching for conversations.
    """

    def before_model_call(self, event: BeforeModelCallEvent) -> None:
        messages = event.messages
        if not messages:
            return
        # Find last assistant message
        last_assistant_idx = None
        for i in reversed(range(len(messages))):
            if messages[i].role == Role.ASSISTANT:
                last_assistant_idx = i
                break
        if last_assistant_idx is None:
            return
        last_assistant_msg = messages[last_assistant_idx]

        # Create cachePoint content block
        # We append a cachePoint dict with type "default" to the content list
        content = list(last_assistant_msg.content)

        # Check if cachePoint already present to avoid duplication
        if content and isinstance(content[-1], dict) and "cachePoint" in content[-1]:
            return

        content.append({"cachePoint": {"type": "default"}})

        # Create new message instance with updated content
        new_message = last_assistant_msg._replace(content=content) if hasattr(last_assistant_msg, '_replace') else None

        # If _replace not available (unlikely), fallback to directly assign content
        if new_message is None:
            last_assistant_msg.content = content
        else:
            messages[last_assistant_idx] = new_message
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
                    # add cache_control from cachePoint, implementing the fix for message-level handling
                    last_content = system_content[-1]
                    if isinstance(last_content, dict):
                        last_content["cache_control"] = {
                            "type": "default",
                        }
                    else:
                        # fallback or ignore if not dict
                        pass
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
                    # add cache_control from cachePoint, implementing the fix for message-level handling
                    last_content = system_content[-1]
                    if isinstance(last_content, dict):
                        last_content["cache_control"] = {
                            "type": "default",
                        }
                    else:
                        # fallback or ignore if not dict
                        pass
</patched>
</file>
```