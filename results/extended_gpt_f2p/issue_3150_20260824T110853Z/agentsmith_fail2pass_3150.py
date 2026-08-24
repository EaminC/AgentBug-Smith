import pytest

import strands
from strands import Agent
from strands._middleware.stages import ExecuteToolStage, MiddlewareInterruptResult, AgentStreamContext
from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent
from strands.interrupt import Interrupt, InterruptException
from strands.types._events import ToolInterruptEvent, ToolResultEvent


@pytest.fixture
def calculator_tool():
    @strands.tool(name="calculator")
    def func(expression: str) -> str:
        """Evaluate a math expression."""
        return str(eval(expression))

    return func


def _tool_use_model(responses_after_tool):
    """Build a model that calls the calculator once, then replays the given responses."""
    tool_use_msg = {
        "role": "assistant",
        "content": [{"toolUse": {"toolUseId": "tool_1", "name": "calculator", "input": {"expression": "2+2"}}}],
    }
    # Use strands.MockedModelProvider from strands.tests.fixtures.mocked_model_provider
    from tests.fixtures.mocked_model_provider import MockedModelProvider

    return MockedModelProvider([tool_use_msg, *responses_after_tool])


@pytest.fixture
def model():
    return _tool_use_model([{"role": "assistant", "content": [{"text": "The answer is 4."}]}])


@pytest.fixture
def agent(model, calculator_tool):
    return Agent(model=model, tools=[calculator_tool], callback_handler=None)


def test_execute_tool_context_interrupt_behavior(agent):
    """Test that ExecuteToolContext.interrupt raises InterruptException on first call and returns response on resume."""

    async def gate(context, next_fn):
        context.interrupt("gate", reason="check")
        async for event in next_fn(context):
            yield event

    agent._middleware_registry.add_middleware(ExecuteToolStage, gate)

    result = agent("what is 2+2?")
    assert result.stop_reason == "interrupt"
    assert len(result.interrupts) == 1
    assert result.interrupts[0].name == "gate"

    # Resume with response
    result2 = agent([{"interruptResponse": {"interruptId": result.interrupts[0].id, "response": "ok"}}])
    assert result2.stop_reason == "end_turn"


def test_execute_tool_context_interrupt_with_preemptive_response(agent):
    """Providing a preemptive response skips the interrupt entirely."""

    async def gate_with_default(context, next_fn):
        interrupt_result = context.interrupt("gate", reason="check", response="pre-approved")
        assert interrupt_result.response == "pre-approved"
        async for event in next_fn(context):
            yield event

    agent._middleware_registry.add_middleware(ExecuteToolStage, gate_with_default)
    result = agent("what is 2+2?")

    assert result.stop_reason == "end_turn"


def test_middleware_interrupt_id_is_deterministic(agent):
    """The interrupt ID is namespaced by tool_use_id."""

    async def gate(context, next_fn):
        context.interrupt("my_gate", reason="check")
        async for event in next_fn(context):
            yield event

    agent._middleware_registry.add_middleware(ExecuteToolStage, gate)

    result = agent("what is 2+2?")
    assert result.interrupts[0].id.startswith("v1:middleware_execute_tool:tool_1:")


def test_middleware_interrupt_short_circuits_tool_execution():
    """When middleware interrupts, the tool does NOT execute."""
    tool_executed = False

    @strands.tool(name="tracked_tool")
    def tracked_tool() -> str:
        nonlocal tool_executed
        tool_executed = True
        return "done"

    tool_use_msg = {
        "role": "assistant",
        "content": [{"toolUse": {"toolUseId": "t1", "name": "tracked_tool", "input": {}}}],
    }
    final_msg = {"role": "assistant", "content": [{"text": "ok"}]}
    from tests.fixtures.mocked_model_provider import MockedModelProvider

    model = MockedModelProvider([tool_use_msg, final_msg])
    agent = Agent(model=model, tools=[tracked_tool], callback_handler=None)

    async def blocker(context, next_fn):
        context.interrupt("block", reason="nope")
        async for event in next_fn(context):
            yield event

    agent._middleware_registry.add_middleware(ExecuteToolStage, blocker)
    result = agent("do it")

    assert result.stop_reason == "interrupt"
    assert not tool_executed


def test_before_hook_fires_but_after_hook_skipped_on_interrupt(calculator_tool):
    """On a middleware interrupt, BeforeToolCallEvent fires but AfterToolCallEvent does not."""
    from tests.fixtures.mock_hook_provider import MockHookProvider

    hook_provider = MockHookProvider(event_types="all")
    model = _tool_use_model([{"role": "assistant", "content": [{"text": "4"}]}])
    agent = Agent(model=model, tools=[calculator_tool], callback_handler=None, hooks=[hook_provider])

    async def gate(context, next_fn):
        context.interrupt("gate", reason="check")
        async for event in next_fn(context):
            yield event

    agent._middleware_registry.add_middleware(ExecuteToolStage, gate)
    result = agent("calc")

    assert result.stop_reason == "interrupt"
    _, events = hook_provider.get_events()
    event_types = [type(event) for event in events]
    assert BeforeToolCallEvent in event_types
    assert AfterToolCallEvent not in event_types


def test_stored_human_response_takes_precedence_over_preemptive(calculator_tool):
    """A stored human response must win over a middleware's preemptive response=."""
    from strands._middleware.stages import _resolve_middleware_interrupt

    interrupt_id = "v1:middleware_execute_tool:tool_1:test-gate"
    interrupts = {interrupt_id: Interrupt(id=interrupt_id, name="gate", response="DENIED")}

    result = _resolve_middleware_interrupt(interrupts, interrupt_id, "gate", None, "auto-approve")

    assert result == MiddlewareInterruptResult(response="DENIED")


def test_agent_stream_context_interrupt_id_and_resolution():
    """AgentStreamContext.interrupt raises, resolves, and produces a stable namespaced id."""
    ctx = AgentStreamContext(agent=None, messages=[], invocation_state={}, _interrupts={})

    interrupt_id = ctx._interrupt_id("gate")
    assert interrupt_id.startswith("v1:middleware_agent_stream:")
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
