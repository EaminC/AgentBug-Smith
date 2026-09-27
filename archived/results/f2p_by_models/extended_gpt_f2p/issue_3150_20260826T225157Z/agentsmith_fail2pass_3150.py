from strands._middleware.stages import MiddlewareInterruptResult, _resolve_middleware_interrupt, AgentStreamContext
from strands.interrupt import Interrupt, InterruptException
import pytest


def test_stored_human_response_takes_precedence_over_preemptive():
    """A stored human response must win over a middleware's preemptive response=.

    Guards against accidentally swapping the two checks in _resolve_middleware_interrupt,
    which would let a middleware default silently override a human decision.
    """
    interrupt_id = "v1:middleware_execute_tool:tool_1:test-gate"
    interrupts = {interrupt_id: Interrupt(id=interrupt_id, name="gate", response="DENIED")}

    result = _resolve_middleware_interrupt(
        interrupts, interrupt_id, "gate", None, "auto-approve"
    )

    assert result == MiddlewareInterruptResult(response="DENIED")


def test_agent_stream_context_interrupt_id_and_resolution():
    """AgentStreamContext.interrupt raises, resolves, and produces a stable namespaced id."""
    ctx = AgentStreamContext(agent=None, messages=[], invocation_state={}, _interrupts={})

    interrupt_id = ctx._interrupt_id("gate")
    assert interrupt_id.startswith("v1:middleware_agent_stream:")
    # The id is stable for the same name
    assert interrupt_id == ctx._interrupt_id("gate")

    with pytest.raises(InterruptException):
        ctx.interrupt("gate")

    resumed = AgentStreamContext(
        agent=None,
        messages=[],
        invocation_state={},
        _interrupts={interrupt_id: Interrupt(id=interrupt_id, name="gate", response="ok")},
    )
    assert resumed.interrupt("gate") == MiddlewareInterruptResult(response="ok")
