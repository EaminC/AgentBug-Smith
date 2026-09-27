```
<file>src/strands/hooks/events.py</file>
<original>from dataclasses import dataclass

from ..types.content import Message
from .registry import HookEvent


@dataclass
class AgentInitializedEvent(HookEvent):
    """Event triggered when an agent has finished initialization.

    This event is fired after the agent has been fully constructed and all
    built-in components have been initialized. Hook providers can use this
    event to perform setup tasks that require a fully initialized agent.
    """

    pass


@dataclass
class BeforeInvocationEvent(HookEvent):
    """Event triggered at the beginning of a new agent request.

    This event is fired before the agent begins processing a new user request,
    before any model inference or tool execution occurs. Hook providers can
    use this event to perform request-level setup, logging, or validation.

    This event is triggered at the beginning of the following api calls:
      - Agent.__call__
      - Agent.stream_async
      - Agent.structured_output
    """

    pass
</original>
<patched>from dataclasses import dataclass

from ..types.content import Message
from .registry import HookEvent


@dataclass
class AgentInitializedEvent(HookEvent):
    """Event triggered when an agent has finished initialization.

    This event is fired after the agent has been fully constructed and all
    built-in components have been initialized. Hook providers can use this
    event to perform setup tasks that require a fully initialized agent.
    """

    pass


@dataclass
class BeforeInvocationEvent(HookEvent):
    """Event triggered at the beginning of a new agent request.

    This event is fired before the agent begins processing a new user request,
    before any model inference or tool execution occurs. Hook providers can
    use this event to perform request-level setup, logging, or validation.

    This event is triggered at the beginning of the following api calls:
      - Agent.__call__
      - Agent.stream_async
      - Agent.structured_output
    """

    pass


@dataclass
class BeforeToolCallEvent(HookEvent):
    """Event triggered before a tool is called.

    This event is fired just before the agent executes a tool, allowing hook
    providers to inspect or modify the tool input or take other actions.
    """

    # Add any properties or methods from the experimental BeforeToolInvocationEvent
    # if needed. This is a placeholder using same structure.
    pass


@dataclass
class AfterToolCallEvent(HookEvent):
    """Event triggered after a tool call completes.

    This event is fired after the agent has finished executing a tool,
    allowing hook providers to inspect the tool's output or take other actions.
    """

    # Add any properties or methods from the experimental AfterToolInvocationEvent
    # if needed. This is a placeholder using same structure.
    pass


@dataclass
class BeforeModelCallEvent(HookEvent):
    """Event triggered before a model call.

    This event is fired just before the agent calls the model for inference,
    allowing hook providers to inspect or modify input.
    """

    # Add any properties or methods from the experimental BeforeModelInvocationEvent
    # if needed. This is a placeholder using same structure.
    pass


@dataclass
class AfterModelCallEvent(HookEvent):
    """Event triggered after a model call completes.

    This event is fired after the agent has finished calling the model,
    allowing hook providers to inspect output or perform further actions.
    """

    # Add any properties or methods from the experimental AfterModelInvocationEvent
    # if needed. This is a placeholder using same structure.
    pass
</patched>
```

```
<file>src/strands/experimental/hooks/__init__.py</file>
<original>"""Experimental hook functionality that has not yet reached stability."""

from .events import (
    AfterModelInvocationEvent,
    AfterToolInvocationEvent,
    BeforeModelInvocationEvent,
    BeforeToolInvocationEvent,
)

__all__ = [
    "BeforeToolInvocationEvent",
    "AfterToolInvocationEvent",
    "BeforeModelInvocationEvent",
    "AfterModelInvocationEvent",
]
</original>
<patched>"""Experimental hook functionality that has not yet reached stability."""

from strands.hooks.events import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    BeforeToolCallEvent,
)

# Aliases to preserve experimental class names pointing to stable new classes
BeforeToolInvocationEvent = BeforeToolCallEvent
AfterToolInvocationEvent = AfterToolCallEvent
BeforeModelInvocationEvent = BeforeModelCallEvent
AfterModelInvocationEvent = AfterModelCallEvent

__all__ = [
    "BeforeToolInvocationEvent",
    "AfterToolInvocationEvent",
    "BeforeModelInvocationEvent",
    "AfterModelInvocationEvent",
]
</patched>
```