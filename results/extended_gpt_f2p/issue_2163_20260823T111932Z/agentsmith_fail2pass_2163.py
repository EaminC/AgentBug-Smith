import asyncio
import pytest
import strands
from strands.event_loop.event_loop import event_loop_cycle
from strands.types.exceptions import MaxTokensReachedException


@pytest.mark.asyncio
async def test_agent_reusable_after_max_tokens_reached():
    """
    Test that after MaxTokensReachedException is raised, the same agent instance can be reused
    for subsequent calls without requiring a full reset.
    """
    # Create a dummy agent with minimal setup
    agent = strands.Agent()
    # Initialize required attributes to avoid AttributeError during event_loop_cycle
    agent.messages = [{"role": "user", "content": [{"text": "Hello"}]}]
    agent.system_prompt = "system prompt"
    agent._system_prompt_content = None
    agent.tool_registry = strands.tools.registry.ToolRegistry()
    agent.event_loop_metrics = strands.telemetry.metrics.EventLoopMetrics()
    agent.event_loop_metrics.reset_usage_metrics()
    agent.hooks = strands.hooks.HookRegistry()
    agent.tool_executor = strands.tools.executors.SequentialToolExecutor()
    agent._interrupt_state = strands.interrupt._InterruptState()
    agent._cancel_signal = asyncio.Event()
    agent._model_state = {}
    agent._middleware_registry = strands._middleware.MiddlewareRegistry()
    agent._checkpointing = False
    agent._checkpoint = None
    agent._checkpoint_cycle_index = 0
    agent._checkpoint_resume_position = None
    agent.trace_attributes = {}
    agent.retry_strategy = strands.event_loop._retry.ModelRetryStrategy()
    agent._cancel_signal = asyncio.Event()  # Use asyncio.Event for async context
    agent._cancel_signal.clear()

    # Define a dummy model that yields a max_tokens stop reason on first call
    async def partial_stream():
        yield {
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "t1",
                        "name": "dummy_tool",
                        "input": {},
                    }
                }
            }
        }
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "max_tokens"}}

    class DummyModel:
        def __init__(self):
            self.call_count = 0

        def stream(self, *args, **kwargs):
            self.call_count += 1
            return partial_stream()

    dummy_model = DummyModel()
    agent.model = dummy_model

    # First call triggers MaxTokensReachedException
    with pytest.raises(MaxTokensReachedException):
        stream = event_loop_cycle(agent=agent, invocation_state={})
        async for _ in stream:
            pass

    # After exception, the agent's messages should contain the partial message
    assert len(agent.messages) > 1
    assert any("tool use was incomplete due" in content.get("text", "") for msg in agent.messages for content in msg.get("content", []) if isinstance(content, dict))

    # The agent instance should remain usable: call event_loop_cycle again with a normal response
    # Patch the model to yield a normal end_turn stop reason on second call
    async def normal_stream():
        yield {"contentBlockDelta": {"delta": {"text": "test after max tokens"}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}

    dummy_model.stream = lambda *a, **k: normal_stream()

    # This call should NOT raise and should produce a normal end_turn stop reason
    stream = event_loop_cycle(agent=agent, invocation_state={})
    last_event = None
    async for event in stream:
        last_event = event

    # The last event should be an EventLoopStopEvent with stop_reason "end_turn"
    assert last_event is not None
    stop = last_event.get("stop")
    assert stop is not None
    stop_reason = stop[0]
    assert stop_reason == "end_turn"
    message = stop[1]
    assert "test after max tokens" in "".join(
        part.get("text", "") for part in message.get("content", []) if isinstance(part, dict)
    )


@pytest.mark.asyncio
async def test_max_tokens_exception_message_update():
    """
    Test that the MaxTokensReachedException message is updated to remove 'unrecoverable state'
    and includes the new informative message.
    """
    agent = strands.Agent()
    agent.messages = [{"role": "user", "content": [{"text": "Hello"}]}]
    agent.system_prompt = "system prompt"
    agent._system_prompt_content = None
    agent.tool_registry = strands.tools.registry.ToolRegistry()
    agent.event_loop_metrics = strands.telemetry.metrics.EventLoopMetrics()
    agent.event_loop_metrics.reset_usage_metrics()
    agent.hooks = strands.hooks.HookRegistry()
    agent.tool_executor = strands.tools.executors.SequentialToolExecutor()
    agent._interrupt_state = strands.interrupt._InterruptState()
    agent._cancel_signal = asyncio.Event()
    agent._cancel_signal.clear()
    agent._model_state = {}
    agent._middleware_registry = strands._middleware.MiddlewareRegistry()
    agent._checkpointing = False
    agent._checkpoint = None
    agent._checkpoint_cycle_index = 0
    agent._checkpoint_resume_position = None
    agent.trace_attributes = {}
    agent.retry_strategy = strands.event_loop._retry.ModelRetryStrategy()

    async def partial_stream():
        yield {
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "t1",
                        "name": "dummy_tool",
                        "input": {},
                    }
                }
            }
        }
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "max_tokens"}}

    class DummyModel:
        def stream(self, *args, **kwargs):
            return partial_stream()

    agent.model = DummyModel()

    expected_message_start = (
        "Model stopped generating due to maximum token limit. "
        "The partial message has been added to the conversation history. "
        "You can continue by calling the agent again. "
    )

    with pytest.raises(MaxTokensReachedException) as excinfo:
        stream = event_loop_cycle(agent=agent, invocation_state={})
        async for _ in stream:
            pass

    assert excinfo.value.args
    assert excinfo.value.args[0].startswith(expected_message_start)


@pytest.mark.asyncio
async def test_agent_state_intact_after_max_tokens_exception():
    """
    Test that after MaxTokensReachedException, the agent's internal state remains intact
    and the agent can still access its messages and other attributes.
    """
    agent = strands.Agent()
    agent.messages = [{"role": "user", "content": [{"text": "Hello"}]}]
    agent.system_prompt = "system prompt"
    agent._system_prompt_content = None
    agent.tool_registry = strands.tools.registry.ToolRegistry()
    agent.event_loop_metrics = strands.telemetry.metrics.EventLoopMetrics()
    agent.event_loop_metrics.reset_usage_metrics()
    agent.hooks = strands.hooks.HookRegistry()
    agent.tool_executor = strands.tools.executors.SequentialToolExecutor()
    agent._interrupt_state = strands.interrupt._InterruptState()
    agent._cancel_signal = asyncio.Event()
    agent._cancel_signal.clear()
    agent._model_state = {}
    agent._middleware_registry = strands._middleware.MiddlewareRegistry()
    agent._checkpointing = False
    agent._checkpoint = None
    agent._checkpoint_cycle_index = 0
    agent._checkpoint_resume_position = None
    agent.trace_attributes = {}
    agent.retry_strategy = strands.event_loop._retry.ModelRetryStrategy()

    async def partial_stream():
        yield {
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "t1",
                        "name": "dummy_tool",
                        "input": {},
                    }
                }
            }
        }
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "max_tokens"}}

    class DummyModel:
        def stream(self, *args, **kwargs):
            return partial_stream()

    agent.model = DummyModel()

    with pytest.raises(MaxTokensReachedException):
        stream = event_loop_cycle(agent=agent, invocation_state={})
        async for _ in stream:
            pass

    # After exception, agent should still have messages attribute intact
    assert hasattr(agent, "messages")
    assert isinstance(agent.messages, list)
    assert len(agent.messages) > 1

    # Agent's tool_registry should still be accessible
    assert hasattr(agent, "tool_registry")
    assert agent.tool_registry is not None

    # Agent's event_loop_metrics should still be accessible and reset_usage_metrics callable
    assert hasattr(agent, "event_loop_metrics")
    assert callable(getattr(agent.event_loop_metrics, "reset_usage_metrics", None))

    # Agent's hooks should still be accessible
    assert hasattr(agent, "hooks")
    assert agent.hooks is not None

    # Agent's tool_executor should still be accessible
    assert hasattr(agent, "tool_executor")
    assert agent.tool_executor is not None

    # Agent's _interrupt_state should still be accessible
    assert hasattr(agent, "_interrupt_state")
    assert agent._interrupt_state is not None

    # Agent's _cancel_signal should still be accessible
    assert hasattr(agent, "_cancel_signal")
    assert agent._cancel_signal is not None

    # Agent's _model_state should still be accessible
    assert hasattr(agent, "_model_state")
    assert isinstance(agent._model_state, dict)

    # Agent's _middleware_registry should still be accessible
    assert hasattr(agent, "_middleware_registry")
    assert agent._middleware_registry is not None

    # Agent's retry_strategy should still be accessible
    assert hasattr(agent, "retry_strategy")
    assert agent.retry_strategy is not None
