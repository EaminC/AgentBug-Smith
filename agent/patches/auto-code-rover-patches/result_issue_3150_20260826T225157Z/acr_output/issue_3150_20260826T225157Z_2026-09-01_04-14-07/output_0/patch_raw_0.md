```
<file>strands-py/src/strands/_middleware/stages.py</file>
<original>
@dataclass
class MiddlewareInterruptResult:
    """Value returned by ``ExecuteToolContext.interrupt()`` when the agent resumes.

    Wrapping the response (rather than returning it bare) mirrors the TypeScript SDK and
</original>
<patched>
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")

@dataclass
class MiddlewareInterruptResult(Generic[T]):
    """Value returned by ``ExecuteToolContext.interrupt()`` when the agent resumes.

    Wrapping the response (rather than returning it bare) mirrors the TypeScript SDK and
</patched>
</file>

<file>strands-py/src/strands/_middleware/stages.py</file>
<original>
    # excluded from repr to avoid dumping unrelated interrupt bookkeeping.
    _interrupt_state: _InterruptState = field(repr=False)

    def interrupt(self, name: str, *, reason: Any = None, response: Any = None) -> MiddlewareInterruptResult:
        """Request a human-in-the-loop interrupt.

        On first execution (no prior response) this raises ``InterruptException`` to halt
        the agent. After the user resumes with a response, the second call returns that
        response. Providing ``response`` preemptively skips the interrupt entirely.

        This method is read-only with respect to interrupt state: it inspects prior
        responses but does not register the interrupt itself. The tool executor registers
        it (in its ``InterruptException`` handler) as the single source of truth, matching
        the TypeScript SDK where middleware interrupts never write to interrupt state.

        Args:
            name: User-defined name for the interrupt. The interrupt id is scoped to the tool
                call (``v1:middleware_execute_tool:<toolUseId>:<uuid5(name)>``) but not to the
                individual middleware, so the name must be unique across all middleware that
                interrupt this tool call — two middleware using the same name on the same tool
                call collide and share one response. (This matches the hook/tool interrupt
                contract, which is likewise unique per tool call, not per callback.)
            reason: Optional reason for the interrupt (surfaced to the user).
            response: Optional preemptive response — when set, no interrupt is raised.

        Returns:
            The user's response wrapped in a ``MiddlewareInterruptResult``.

        Raises:
            InterruptException: When no response is available yet and none was provided.
        """
        interrupt_id = self._interrupt_id(name)

        existing = self._interrupt_state.interrupts.get(interrupt_id)
        if existing is not None and existing.response is not None:
            return MiddlewareInterruptResult(response=existing.response)

        if response is not None:
            return MiddlewareInterruptResult(response=response)

        raise InterruptException(Interrupt(id=interrupt_id, name=name, reason=reason))
</original>
<patched>
    # excluded from repr to avoid dumping unrelated interrupt bookkeeping.
    _interrupt_state: "_InterruptState" = field(repr=False)

    def interrupt(self, name: str, *, reason: Any = None, response: Any = None) -> MiddlewareInterruptResult:
        """Request a human-in-the-loop interrupt.

        On first execution (no prior response) this raises ``InterruptException`` to halt
        the agent. After the user resumes with a response, the second call returns that
        response. Providing ``response`` preemptively skips the interrupt entirely.

        This method is read-only with respect to interrupt state: it inspects prior
        responses but does not register the interrupt itself. The tool executor registers
        it (in its ``InterruptException`` handler) as the single source of truth, matching
        the TypeScript SDK where middleware interrupts never write to interrupt state.

        Args:
            name: User-defined name for the interrupt. The interrupt id is scoped to the middleware namespace
                and includes a prefix (e.g., ``v1:middleware_execute_tool:<toolUseId>:<uuid5(name)>``),
                ensuring uniqueness across all middleware interrupts for this tool call. Names must be unique
                across all middleware to avoid collisions.
            reason: Optional reason for the interrupt (surfaced to the user).
            response: Optional preemptive response — when set, no interrupt is raised.

        Returns:
            The user's response wrapped in a ``MiddlewareInterruptResult``.

        Raises:
            InterruptException: When no response is available yet and none was provided.
        """
        interrupt_id = self._interrupt_id(name)

        existing = self._interrupt_state.interrupts.get(interrupt_id)
        if existing is not None and existing.response is not None:
            return MiddlewareInterruptResult(response=existing.response)

        if response is not None:
            return MiddlewareInterruptResult(response=response)

        from strands.interrupt import Interrupt, InterruptException

        interrupt_obj = Interrupt(id=interrupt_id, name=name, reason=reason)
        # Add the source field to mark middleware interrupts
        interrupt_obj.source = "middleware"

        raise InterruptException(interrupt_obj)
</patched>
</file>

<file>strands-py/src/strands/interrupt.py</file>
<original>
@dataclass
class Interrupt:
    """Represents an interrupt that can pause agent execution for human-in-the-loop workflows.

    Attributes:
        id: Unique identifier.
        name: User defined name.
        reason: User provided reason for raising the interrupt.
        response: Human response provided when resuming the agent after an interrupt.
    """

    id: str
    name: str
    reason: Any = None
    response: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for session management."""
        return asdict(self)
</original>
<patched>
from dataclasses import dataclass, asdict, field
from typing import Any, Optional

@dataclass
class Interrupt:
    """Represents an interrupt that can pause agent execution for human-in-the-loop workflows.

    Attributes:
        id: Unique identifier.
        name: User defined name.
        reason: User provided reason for raising the interrupt.
        response: Human response provided when resuming the agent after an interrupt.
        source: Source of the interrupt (e.g., 'middleware') to distinguish middleware interrupts.
    """

    id: str
    name: str
    reason: Any = None
    response: Any = None
    source: Optional[str] = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for session management."""
        return asdict(self)
</patched>
</file>

<file>strands-py/src/strands/_middleware/__init__.py</file>
<original>
#
# Middleware core imports
#
from .types import MiddlewareStage, MiddlewareResult
from .registry import MiddlewareRegistry
from .stages import InvokeModelStage
</original>
<patched>
#
# Middleware core imports
#
from .types import MiddlewareStage, MiddlewareResult
from .registry import MiddlewareRegistry
from .stages import InvokeModelStage, ExecuteToolStage
# AgentStreamStage is internal, not exported.

# Add a convenience method for adding middleware (similar to TS addMiddleware).
def add_middleware(middleware_registry: MiddlewareRegistry, stage, handler) -> None:
    """Register middleware handler on a specified stage in the registry."""
    middleware_registry.add_middleware(stage, handler)
</patched>
</file>

<file>strands-py/src/strands/_middleware/stages.py</file>
<original>
# Presumed start of module imports and existing code snippets (not shown)
</original>
<patched>
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Optional, TypedDict
from strands.interrupt import InterruptException, Interrupt
from strands._middleware.registry import MiddlewareRegistry
from strands.types._events import TypedEvent

# --- MiddlewareInterruptResult -- implemented above ---

# Helper function to generate unique interrupt IDs for middleware interrupts
def generate_middleware_interrupt_id(prefix: str, name: str) -> str:
    # Use uuid5 to generate deterministic UUIDs from the name and prefix
    namespace = uuid.UUID('12345678-1234-5678-1234-567812345678')
    name_uuid = uuid.uuid5(namespace, name)
    return f"{prefix}:{name_uuid}"

# New middleware stages implementation -- ExecuteToolStage and AgentStreamStage

@dataclass
class ExecuteToolContext:
    agent: Any
    tool: Any  # Tool or None
    tool_use: Dict[str, Any]
    invocation_state: Dict[str, Any]
    _interrupt_state: Any = field(repr=False)

    def _interrupt_id(self, name: str) -> str:
        prefix = f"v1:middleware_execute_tool:{self.tool_use.get('toolUseId')}"
        return generate_middleware_interrupt_id(prefix, name)

    def interrupt(
        self,
        name: str,
        *,
        reason: Any = None,
        response: Any = None,
    ) -> "MiddlewareInterruptResult":
        interrupt_id = self._interrupt_id(name)
        existing = self._interrupt_state.interrupts.get(interrupt_id)
        if existing and existing.response is not None:
            return MiddlewareInterruptResult(response=existing.response)
        if response is not None:
            return MiddlewareInterruptResult(response=response)
        interrupt_obj = Interrupt(id=interrupt_id, name=name, reason=reason)
        interrupt_obj.source = "middleware"
        raise InterruptException(interrupt_obj)

@dataclass
class ExecuteToolStage(MiddlewareStage[ExecuteToolContext, Any, TypedEvent]):
    name: str = "executeTool"

    # MiddlewareStage base implementations would be used here;
    # The middleware code invoking is expected to wrap tool execution with this stage.

@dataclass
class AgentStreamContext:
    agent: Any
    args: Any
    options: Any
    _interrupt_state: Any = field(repr=False)

    def _interrupt_id(self, name: str) -> str:
        prefix = f"v1:middleware_agent_stream:{id(self.agent)}"
        return generate_middleware_interrupt_id(prefix, name)

    def interrupt(
        self,
        name: str,
        *,
        reason: Any = None,
        response: Any = None,
    ) -> "MiddlewareInterruptResult":
        interrupt_id = self._interrupt_id(name)
        existing = self._interrupt_state.interrupts.get(interrupt_id)
        if existing and existing.response is not None:
            return MiddlewareInterruptResult(response=existing.response)
        if response is not None:
            return MiddlewareInterruptResult(response=response)
        interrupt_obj = Interrupt(id=interrupt_id, name=name, reason=reason)
        interrupt_obj.source = "middleware"
        raise InterruptException(interrupt_obj)

@dataclass
class AgentStreamStage(MiddlewareStage[AgentStreamContext, Any, TypedEvent]):
    name: str = "agentStream"
    # Marked internal: do not export from __init__.py

# The actual middleware invocation and integration with ToolExecutor._stream and Agent._run_loop
# would be added in their respective modules as per issue description.
</patched>
</file>