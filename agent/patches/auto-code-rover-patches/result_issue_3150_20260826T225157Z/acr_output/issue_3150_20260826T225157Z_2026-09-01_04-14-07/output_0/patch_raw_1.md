The key missing pieces from the existing Python codebase, necessary to fully port the remaining middleware stages (`ExecuteToolStage`, `AgentStreamStage`) and the middleware interrupt path from TypeScript, are:

- Addition of a `source` attribute on the `Interrupt` dataclass to mark middleware-originated interrupts.
- Implementation of a MiddlewareInterruptible base or mixin to provide the `interrupt` method and middleware interrupting behavior.
- Implementation of the `create_middleware_interrupt` factory function to create middleware interrupts with correct id prefixing and source annotation.
- Adding the two new middleware stages (`ExecuteToolStage`, `AgentStreamStage`) in `_middleware/stages.py`.
- Wiring these stages into the respective locations: wrapping tool execution in `ToolExecutor._stream`, wrapping agent event loop `_run_loop`.
- Exporting public stages appropriately and hiding the internal `AgentStreamStage`, ensuring middleware registration support.

The patch below contains the necessary additions and modifications in the relevant files, implementing the missing interrupt mechanics and middleware stages as described.

---

# modification 1: Add `source` field to `Interrupt` and update serialization.

```
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
@dataclass
class Interrupt:
    """Represents an interrupt that can pause agent execution for human-in-the-loop workflows.

    Attributes:
        id: Unique identifier.
        name: User defined name.
        reason: User provided reason for raising the interrupt.
        response: Human response provided when resuming the agent after an interrupt.
        source: Origin of the interrupt, e.g. "middleware"
    """

    id: str
    name: str
    reason: Any = None
    response: Any = None
    source: str = ""  # empty string for backward compatibility if unset

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for session management."""
        d = asdict(self)
        # Always include source field to distinguish middleware interrupts
        d.setdefault("source", self.source)
        return d
</patched>
```

---

# modification 2: Implement MiddlewareInterruptible base class and create_middleware_interrupt factory function in `_middleware/stages.py`.

```
<file>strands-py/src/strands/_middleware/stages.py</file>
<original>
@dataclass
class MiddlewareInterruptResult:
    """Value returned by ``ExecuteToolContext.interrupt()`` when the agent resumes.

    Wrapping the response (rather than returning it bare) mirrors the TypeScript SDK and
</original>
<patched>
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Generic, TypeVar

# Existing imports and code here
...

@dataclass
class MiddlewareInterruptResult:
    """Value returned by ``ExecuteToolContext.interrupt()`` when the agent resumes.

    Wrapping the response (rather than returning it bare) mirrors the TypeScript SDK and
</patched>
```

*Note:* The above is the original start of the file; following it, add the following classes/functions:

```
TResponse = TypeVar("TResponse")


class MiddlewareInterruptible:
    """Base class providing interrupt support for middleware stage contexts."""

    _interrupt_state: Any  # Expected to be _InterruptState or similar to track interrupts

    def _interrupt_id(self, name: str) -> str:
        # Compose a unique interrupt id with a prefix; subclasses should override if needed
        raise NotImplementedError("MiddlewareInterruptible does not implement _interrupt_id")

    def interrupt(
        self,
        name: str,
        *,
        reason: Any = None,
        response: TResponse | None = None,
    ) -> MiddlewareInterruptResult:
        """Request a human-in-the-loop interrupt.

        On first execution (no prior response) this raises ``InterruptException`` to halt
        the agent. After user resumes with a response, second call returns that response.
        Providing ``response`` preemptively skips raising the interrupt.

        This method is read-only to interrupt state: it inspects prior responses but does
        not register the interrupt itself. The tool executor or agent registers it
        separately, matching TypeScript behavior where middleware interrupts never write
        to interrupt state.

        Args:
            name: Unique user-defined name for the interrupt. Scoped to the context.
            reason: Optional reason string or data for user context.
            response: Optional preemptive response to skip raising interrupt.

        Returns:
            MiddlewareInterruptResult wrapping the user response.

        Raises:
            InterruptException: if no response is available yet and none provided.
        """
        interrupt_id = self._interrupt_id(name)
        existing = self._interrupt_state.interrupts.get(interrupt_id)
        if existing is not None and existing.response is not None:
            return MiddlewareInterruptResult(response=existing.response)

        if response is not None:
            return MiddlewareInterruptResult(response=response)

        # Raise InterruptException with Interrupt object including source="middleware"
        from strands.interrupt import Interrupt, InterruptException

        interrupt_obj = Interrupt(id=interrupt_id, name=name, reason=reason, source="middleware")
        raise InterruptException(interrupt_obj)


def create_middleware_interrupt(
    interrupt_state: Any,
    id_prefix: str,
) -> MiddlewareInterruptible:
    """Create a non-mutating middleware interrupt object with prefixed IDs.

    Args:
        interrupt_state: The global interrupt state tracking all interrupts.
        id_prefix: Prefix to uniquely identify interrupt contexts.

    Returns:
        MiddlewareInterruptible object usable in middleware contexts.
    """

    class _MiddlewareInterrupt(MiddlewareInterruptible):
        def __init__(self) -> None:
            self._interrupt_state = interrupt_state

        def _interrupt_id(self, name: str) -> str:
            # Compose a stable id for the interrupt, e.g. using uuid5 with id_prefix + name
            import hashlib

            # To maintain compatibility with TypeScript v1: generate string id as
            # f"{id_prefix}:{name}"
            # For stricter uniqueness, could use uuid5 based on namespace and name
            # Here we use simple prefixing for clarity
            return f"{id_prefix}:{name}"

    return _MiddlewareInterrupt()
```

---

# modification 3: Add new middleware stages `ExecuteToolStage` and internal `AgentStreamStage` in `_middleware/stages.py`, export public ones

*Add near top or after MiddlewareInterruptResult:*

```
from .types import MiddlewareStage

@dataclass
class ExecuteToolContext(MiddlewareInterruptible):
    agent: Any
    tool: Any | None
    tool_use: dict[str, Any]
    invocation_state: dict[str, Any]
    _interrupt_state: Any = field(repr=False)

    def _interrupt_id(self, name: str) -> str:
        tool_use_id = self.tool_use.get("toolUseId", "unknown")
        id_prefix = f"v1:middleware_execute_tool:{tool_use_id}"
        return f"{id_prefix}:{name}"


ExecuteToolStage: MiddlewareStage[ExecuteToolContext, Any, Any] = MiddlewareStage(name="executeTool")
"""Middleware stage wrapping a single tool execution.

Middleware can short-circuit execution, intercept interrupts, and observe context.
"""

@dataclass
class AgentStreamContext(MiddlewareInterruptible):
    agent: Any
    args: tuple[Any, ...]
    options: dict[str, Any]
    _interrupt_state: Any = field(repr=False)

    def _interrupt_id(self, name: str) -> str:
        id_prefix = "v1:middleware_agent_stream"
        return f"{id_prefix}:{name}"


AgentStreamStage: MiddlewareStage[AgentStreamContext, Any, Any] = MiddlewareStage(name="agentStream")
"""Internal middleware stage wrapping the entire agent output stream.

Not exported publicly to users.
"""
```

---

# modification 4: Modify `ToolExecutor._stream` to wrap tool execution in `ExecuteToolStage` middleware invocation

```
<file>strands-py/src/strands/tools/executors/_executor.py</file>
<original>
    @staticmethod
    async def _stream(
        agent: "Agent | BidiAgent",
        tool_use: ToolUse,
        tool_results: list[ToolResult],
        invocation_state: dict[str, Any],
        structured_output_context: StructuredOutputContext | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[TypedEvent, None]:
        """Stream tool events.

        This method adds additional logic to the stream invocation including:

        - Tool lookup and validation
        - Before/after hook execution
        - Tracing and metrics collection
        - Error handling and recovery
        - Interrupt handling for human-in-the-loop workflows

        Args:
            agent: The agent (Agent or BidiAgent) for which the tool is being executed.
            tool_use: Metadata and inputs for the tool to be executed.
            tool_results: List of tool results from each tool execution.
            invocation_state: Context for the tool invocation.
            structured_output_context: Context for structured output management.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Tool events with the last being the tool result.
        """
        logger.debug("tool_use=<%s> | streaming", tool_use)
        tool_name = tool_use["name"]
        structured_output_context = structured_output_context or StructuredOutputContext()

        tool_info = agent.tool_registry.dynamic_tools.get(tool_name)
        tool_func = tool_info if tool_info is not None else agent.tool_registry.registry.get(tool_name)
        tool_spec = tool_func.tool_spec if tool_func is not None else None

        current_span = trace_api.get_current_span()
        if current_span and tool_spec is not None:
            current_span.set_attribute("gen_ai.tool.description", tool_spec["description"])
            input_schema = tool_spec["inputSchema"]
            if "json" in input_schema:
                current_span.set_attribute("gen_ai.tool.json_schema", serialize(input_schema["json"]))

        invocation_state.update(
            {
                "agent": agent,
                "model": agent.model,
                "messages": agent.messages,
                "system_prompt": agent.system_prompt,
                "tool_config": ToolConfig(  # for backwards compatibility
                    tools=[{"toolSpec": tool_spec} for tool_spec in agent.tool_registry.get_all_tool_specs()],
                    toolChoice=cast(ToolChoice, {"auto": ToolChoiceAuto()}),
                ),
            }
        )

        # Retry loop for tool execution - hooks can set after_event.retry = True to retry
        while True:
            before_event, interrupts = await ToolExecutor._invoke_before_tool_call_hook(
                agent, tool_func, tool_use, invocation_state
            )

            if interrupts:
                yield ToolInterruptEvent(tool_use, interrupts)
                return

            if before_event.cancel_tool:
                cancel_message = (
                    before_event.cancel_tool if isinstance(before_event.cancel_tool, str) else "tool cancelled by user"
                )
                yield ToolCancelEvent(tool_use, cancel_message)

                cancel_result: ToolResult = {
                    "toolUseId": str(tool_use.get("toolUseId")),
                    "status": "error",
                    "content": [{"text": cancel_message}],
                }

                after_event, _ = await ToolExecutor._invoke_after_tool_call_hook(
                    agent,
                    None,
                    tool_use,
                    invocation_state,
                    cancel_result,
                    cancel_message=cancel_message,
                )
                yield ToolResultEvent(after_event.result)
                tool_results.append(after_event.result)
                return

            try:
                selected_tool = before_event.selected_tool
                tool_use = before_event.tool_use
                invocation_state = before_event.invocation_state

                if not selected_tool:
                    # Unknown tool: log here, but do NOT short-circuit. The middleware chain
                    # still runs with ctx.tool = None (matching TS), so middleware can observe
                    # or mock the call; the terminal produces the unknown-tool error result.
                    if tool_func == selected_tool:
                        logger.error(
                            "tool_name=<%s>, available_tools=<%s> | tool not found in registry",
                            tool_name,
                            list(agent.tool_registry.registry.keys()),
                        )
                    else:
                        logger.debug(
                            "tool_name=<%s>, tool_use_id=<%s> | a hook resulted in a non-existing tool call",
                            tool_name,
                            str(tool_use.get("toolUseId")),
                        )
                if structured_output_context.is_enabled:
                    kwargs["structured_output_context"] = structured_output_context

                # Run tool execution through the ExecuteToolStage middleware chain. The
                # terminal streams the tool and yields a plain ToolResultEvent as the last
                # (result) event; middleware can transform inputs/result, short-circuit with
                # a cached result, or gate execution behind an interrupt. A shallow copy of
                # tool_use guards its top-level keys (e.g. name, toolUseId) from accidental
                # in-place edits; its `input` can hold arbitrary, non-copyable objects (e.g.
                # the agent injected on direct tool calls) so it is shared by reference.
                # Middleware wanting an isolated tool_use should pass one via replace().
                middleware_context = ExecuteToolContext(
                    agent=agent,
                    tool=selected_tool,
                    tool_use=dict(tool_use),  # type: ignore[arg-type]
                    invocation_state=invocation_state,
                    _interrupt_state=agent._interrupt_state,
                )

                result_event: ToolResultEvent | None = None
                async for event in agent._middleware_registry.invoke(
                    ExecuteToolStage,
                    middleware_context,
                    _make_execute_tool_terminal(kwargs),
                ):
                    # Tool-originated interrupt: a ToolInterruptEvent yielded from tool.stream()
                    # (including sub-agent interrupts propagated via _AgentAsTool). Distinct from
                    # the middleware-initiated InterruptException handled below — this one rides
                    # the event stream rather than unwinding it. Register its interrupts so
                    # _interrupt_state.resume() can locate them by id, surface the event, and
                    # short-circuit here: a halted tool has no result, so the after-hook and the
                    # result handling below are intentionally skipped.
                    if isinstance(event, ToolInterruptEvent):
                        for interrupt in event.interrupts:
                            agent._interrupt_state.interrupts.setdefault(interrupt.id, interrupt)
                        yield event
                        return

                    # Capture the result but keep draining: middleware may yield trailing
                    # events after it, and the last ToolResultEvent wins (matching the model
                    # stage). It is re-emitted only after AfterToolCallEvent runs, since hooks
                    # may rewrite it. All non-result events flow through as they arrive.
                    if isinstance(event, ToolResultEvent):
                        result_event = event
                    else:
                        yield event

                if result_event is None:
                    raise RuntimeError(
                        "ExecuteToolStage middleware chain did not yield a ToolResultEvent. "
                        "Ensure middleware forwards events from next()."
                    )

                result = result_event.tool_result
                exception = result_event.exception

                after_event, _ = await ToolExecutor._invoke_after_tool_call_hook(
                    agent, selected_tool, tool_use, invocation_state, result, exception=exception
                )

                if ToolExecutor._should_retry(agent, after_event):
                    logger.debug("tool_name=<%s> | retry requested, retrying tool call", tool_name)
                    continue

                yield ToolResultEvent(after_event.result, exception=after_event.exception)
                tool_results.append(after_event.result)
                return

            except InterruptException as interrupt_exception:
                # Middleware-initiated interrupt (context.interrupt() with no response yet).
                # interrupt() is read-only, so this handler is the single place the interrupt
                # is registered before surfacing a ToolInterruptEvent to halt the agent,
                # matching how hook/tool interrupts are reported.
                agent._interrupt_state.interrupts.setdefault(
                    interrupt_exception.interrupt.id, interrupt_exception.interrupt
                )
                yield ToolInterruptEvent(tool_use, [interrupt_exception.interrupt])
                return

            except Exception as e:
                logger.exception("tool_name=<%s> | failed to process tool", tool_name)
                error_result: ToolResult = {
                    "toolUseId": str(tool_use.get("toolUseId")),
                    "status": "error",
                    "content": [{"text": f"Error: {str(e)}"}],
                }

                after_event, _ = await ToolExecutor._invoke_after_tool_call_hook(
                    agent, selected_tool, tool_use, invocation_state, error_result, exception=e
                )
                if ToolExecutor._should_retry(agent, after_event):
                    logger.debug("tool_name=<%s> | retry requested after exception, retrying tool call", tool_name)
                    continue
                yield ToolResultEvent(after_event.result, exception=after_event.exception)
                tool_results.append(after_event.result)
                return
</original>
<patched>
    @staticmethod
    async def _stream(
        agent: "Agent | BidiAgent",
        tool_use: ToolUse,
        tool_results: list[ToolResult],
        invocation_state: dict[str, Any],
        structured_output_context: StructuredOutputContext | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[TypedEvent, None]:
        """Stream tool events.

        This method adds additional logic to the stream invocation including:

        - Tool lookup and validation
        - Before/after hook execution
        - Tracing and metrics collection
        - Error handling and recovery
        - Interrupt handling for human-in-the-loop workflows

        Args:
            agent: The agent (Agent or BidiAgent) for which the tool is being executed.
            tool_use: Metadata and inputs for the tool to be executed.
            tool_results: List of tool results from each tool execution.
            invocation_state: Context for the tool invocation.
            structured_output_context: Context for structured output management.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Tool events with the last being the tool result.
        """
        logger.debug("tool_use=<%s> | streaming", tool_use)
        tool_name = tool_use["name"]
        structured_output_context = structured_output_context or StructuredOutputContext()

        tool_info = agent.tool_registry.dynamic_tools.get(tool_name)
        tool_func = tool_info if tool_info is not None else agent.tool_registry.registry.get(tool_name)
        tool_spec = tool_func.tool_spec if tool_func is not None else None

        current_span = trace_api.get_current_span()
        if current_span and tool_spec is not None:
            current_span.set_attribute("gen_ai.tool.description", tool_spec["description"])
            input_schema = tool_spec["inputSchema"]
            if "json" in input_schema:
                current_span.set_attribute("gen_ai.tool.json_schema", serialize(input_schema["json"]))

        invocation_state.update(
            {
                "agent": agent,
                "model": agent.model,
                "messages": agent.messages,
                "system_prompt": agent.system_prompt,
                "tool_config": ToolConfig(  # for backwards compatibility
                   