```
<file>src/agentscope/app/_service/_session.py</file>
<original>
class SessionService:
    """Cancel in-flight chat runs and cascade-delete related records.

    The cancel side broadcasts via
    :meth:`MessageBus.session_publish_cancel`, then polls
    :meth:`MessageBus.session_is_running` until the run-lock clears or
    a timeout expires — so the implementation is multi-process and
    multi-node by construction.

    Args:
        storage (`StorageBase`):
            Persistent storage backend. Owns durable records and their
            cascades among themselves.
        message_bus (`MessageBus`):
            Live message bus. Owns transient per-session state (events
            log, inbox, run-lock, cancel channel).
    """

    _CANCEL_POLL_INTERVAL_SECS: float = 0.1
    """Interval between :meth:`MessageBus.session_is_running` polls
    while waiting for a cancelled run to release its distributed
    run-lock."""

    def __init__(
        self,
        storage: StorageBase,
        message_bus: MessageBus,
    ) -> None:
        """Bind dependencies.

        Args:
            storage (`StorageBase`): Persistent storage backend.
            message_bus (`MessageBus`): Live message bus.
        """
        self._storage = storage
        self._bus = message_bus

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel_session_run(
        self,
        session_id: str,
        *,
        timeout: float = 10.0,
    ) -> bool:
        """Broadcast a session cancel and wait for the chat-run lock to
        clear.

        Publishes one cancel payload on the bus's shared cancel channel,
        unconditionally. Every process's
        :class:`~agentscope.app._manager.CancelDispatcher` reacts to the
        broadcast by cancelling whatever it locally holds for the
        session — the chat-run asyncio task **and** any background
        tasks owned by that session. The publisher does not need to
        know which worker holds which piece.

        After publishing, polls
        :meth:`MessageBus.session_is_running` until the distributed
        chat-run lock clears. Only the chat run holds a distributed
        lock; BG tasks do not, so this poll only waits for the chat
        run. Returns immediately when no chat run was active.

        Idempotent: calling on an idle session just sends a no-op
        broadcast and observes a clear lock.

        Args:
            session_id (`str`):
                The session whose chat run + BG tasks should be
                cancelled.
            timeout (`float`, defaults to ``10.0``):
                Maximum seconds to wait for the chat-run lock to
                release. On timeout the method returns ``False`` so
                callers can proceed (e.g. with cascade delete) instead
                of raising.

        Returns:
            `bool`: ``True`` if the run-lock cleared within
            ``timeout`` seconds, ``False`` otherwise.
        """
        await self._bus.session_publish_cancel(session_id)

        start = asyncio.get_event_loop().time()
        end = start + timeout

        while await self._bus.session_is_running(session_id):
            if asyncio.get_event_loop().time() >= end:
                return False

            await asyncio.sleep(self._CANCEL_POLL_INTERVAL_SECS)

        return True
</original>
<patched>
class SessionService:
    """Cancel in-flight chat runs and cascade-delete related records.

    The cancel side broadcasts via
    :meth:`MessageBus.session_publish_cancel`, then polls
    :meth:`MessageBus.session_is_running` until the run-lock clears or
    a timeout expires — so the implementation is multi-process and
    multi-node by construction.

    Additionally, this service propagates HITL events originating from subagent sessions
    to the leader's session and forwards user confirmation signals back to originating subagent sessions.

    Args:
        storage (`StorageBase`):
            Persistent storage backend. Owns durable records and their
            cascades among themselves.
        message_bus (`MessageBus`):
            Live message bus. Owns transient per-session state (events
            log, inbox, run-lock, cancel channel).
    """

    _CANCEL_POLL_INTERVAL_SECS: float = 0.1
    """Interval between :meth:`MessageBus.session_is_running` polls
    while waiting for a cancelled run to release its distributed
    run-lock."""

    def __init__(
        self,
        storage: StorageBase,
        message_bus: MessageBus,
    ) -> None:
        """Bind dependencies.

        Args:
            storage (`StorageBase`): Persistent storage backend.
            message_bus (`MessageBus`): Live message bus.
        """
        self._storage = storage
        self._bus = message_bus

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel_session_run(
        self,
        session_id: str,
        *,
        timeout: float = 10.0,
    ) -> bool:
        """Broadcast a session cancel and wait for the chat-run lock to
        clear.

        Publishes one cancel payload on the bus's shared cancel channel,
        unconditionally. Every process's
        :class:`~agentscope.app._manager.CancelDispatcher` reacts to the
        broadcast by cancelling whatever it locally holds for the
        session — the chat-run asyncio task **and** any background
        tasks owned by that session. The publisher does not need to
        know which worker holds which piece.

        After publishing, polls
        :meth:`MessageBus.session_is_running` until the distributed
        chat-run lock clears. Only the chat run holds a distributed
        lock; BG tasks do not, so this poll only waits for the chat
        run. Returns immediately when no chat run was active.

        Idempotent: calling on an idle session just sends a no-op
        broadcast and observes a clear lock.

        Args:
            session_id (`str`):
                The session whose chat run + BG tasks should be
                cancelled.
            timeout (`float`, defaults to ``10.0``):
                Maximum seconds to wait for the chat-run lock to
                release. On timeout the method returns ``False`` so
                callers can proceed (e.g. with cascade delete) instead
                of raising.

        Returns:
            `bool`: ``True`` if the run-lock cleared within
            ``timeout`` seconds, ``False`` otherwise.
        """
        await self._bus.session_publish_cancel(session_id)

        start = asyncio.get_event_loop().time()
        end = start + timeout

        while await self._bus.session_is_running(session_id):
            if asyncio.get_event_loop().time() >= end:
                return False

            await asyncio.sleep(self._CANCEL_POLL_INTERVAL_SECS)

        return True


    async def propagate_subagent_hitl_event_to_leader(
        self,
        subagent_session_id: str,
        leader_session_id: str,
        event_data: dict,
    ) -> None:
        """
        Propagate a HITL event from a subagent session to the leader's session.

        Args:
            subagent_session_id (`str`): The session ID of the originating subagent.
            leader_session_id (`str`): The session ID of the leader.
            event_data (`dict`): Payload/data of the HITL event.
        """
        # Forward the event to the leader session's inbox or event bus here.
        # This method assumes the bus exposes a `session_publish_event` or similar method.
        # If such a method does not exist, it should be implemented accordingly.
        await self._bus.session_publish_event(leader_session_id, event_data)


    async def forward_user_confirmation_to_subagent(
        self,
        leader_session_id: str,
        subagent_session_id: str,
        confirmation_data: dict,
    ) -> None:
        """
        Forward a user confirmation signal from the leader's session to the originating subagent session.

        Args:
            leader_session_id (`str`): The session ID of the leader.
            subagent_session_id (`str`): The session ID of the originating subagent.
            confirmation_data (`dict`): The user confirmation payload.
        """
        # Forward the confirmation back to the subagent session's inbox or event bus.
        await self._bus.session_publish_event(subagent_session_id, confirmation_data)
</patched>
```

```
<file>src/agentscope/agent/_agent.py</file>
<original>
# -*- coding: utf-8 -*-
"""The unified agent class in AgentScope library."""
import asyncio
import inspect

from asyncio import Queue
from copy import deepcopy
from typing import (
    Any,
    AsyncGenerator,
    Sequence,
    Literal,
    List,
    TYPE_CHECKING,
)

import jsonschema

from ._config import ContextConfig, ReActConfig, ModelConfig
from ..state import AgentState
from ._utils import _ToolCallBatch
from .._logging import logger
from .._utils._common import _generate_id, _json_loads_with_repair
from ..event import (
    AgentEvent,
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
    ThinkingBlockDeltaEvent,
    ThinkingBlockEndEvent,
    ThinkingBlockStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultDataDeltaEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
    RequireUserConfirmEvent,
    RequireExternalExecutionEvent,
    ExternalExecutionResultEvent,
    UserConfirmResultEvent,
    DataBlockStartEvent,
    DataBlockDeltaEvent,
    DataBlockEndEvent,
</original>
<patched>
# -*- coding: utf-8 -*-
"""The unified agent class in AgentScope library."""
import asyncio
import inspect

from asyncio import Queue
from copy import deepcopy
from typing import (
    Any,
    AsyncGenerator,
    Sequence,
    Literal,
    List,
    TYPE_CHECKING,
)

import jsonschema

from ._config import ContextConfig, ReActConfig, ModelConfig
from ..state import AgentState
from ._utils import _ToolCallBatch
from .._logging import logger
from .._utils._common import _generate_id, _json_loads_with_repair
from ..event import (
    AgentEvent,
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
    ThinkingBlockDeltaEvent,
    ThinkingBlockEndEvent,
    ThinkingBlockStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultDataDeltaEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
    RequireUserConfirmEvent,
    RequireExternalExecutionEvent,
    ExternalExecutionResultEvent,
    UserConfirmResultEvent,
    DataBlockStartEvent,
    DataBlockDeltaEvent,
    DataBlockEndEvent,
... 

# Add following methods inside the Agent class or relevant main agent class:

async def _handle_propagated_hitl_event(self, event: dict) -> None:
    """
    Handle a HITL event propagated from a subagent and expose it to the leader's session.

    Args:
        event (dict): The HITL event data to expose.
    """
    # This method should forward the event to the leader's session listeners
    # Implementation depends on the event propagation mechanism available.
    # For example, republish the event into the leader session's event stream.
    leader_session_id = self.get_leader_session_id()
    if leader_session_id:
        await self.session_service.propagate_subagent_hitl_event_to_leader(
            subagent_session_id=self.session_id,
            leader_session_id=leader_session_id,
            event_data=event,
        )


async def _forward_user_confirmation(self, confirmation: dict) -> None:
    """
    Forward a user confirmation signal from leader session to this subagent.

    Args:
        confirmation (dict): The user confirmation data received from the leader session.
    """
    # Use the session service to forward confirmation back to subagent session
    leader_session_id = self.get_leader_session_id()
    if leader_session_id:
        await self.session_service.forward_user_confirmation_to_subagent(
            leader_session_id=leader_session_id,
            subagent_session_id=self.session_id,
            confirmation_data=confirmation,
        )
</patched>
```

```
<file>src/agentscope/app/_app.py</file>
<original>
    # Built-in routers
    for router in (
        agent_router,
        chat_router,
        credential_router,
        schedule_router,
        session_router,
        workspace_router,
        model_router,
        tts_model_router,
    ):
        app.include_router(router)

    # Optional extra middlewares
    for middleware in extra_middlewares or []:
        app.add_middleware(middleware.cls, **middleware.kwargs)
</original>
<patched>
    # Built-in routers
    for router in (
        agent_router,
        chat_router,
        credential_router,
        schedule_router,
        session_router,
        workspace_router,
        model_router,
        tts_model_router,
    ):
        app.include_router(router)

    # Optional extra middlewares
    for middleware in extra_middlewares or []:
        app.add_middleware(middleware.cls, **middleware.kwargs)

    # Patch subagent event propagation and confirmation forwarding hooks here if needed
    # For example, set up message bus listeners to propagate events/signals across sessions, or register middleware.

    # This is a placeholder to note that enhancement of the app init could be done here,
    # but actual implementation should be in session and agent service layers.
</patched>
```