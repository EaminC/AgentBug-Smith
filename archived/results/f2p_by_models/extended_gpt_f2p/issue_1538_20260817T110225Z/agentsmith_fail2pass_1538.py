import pytest
import asyncio

@pytest.fixture
def interrupt_hook():
    from strands.hooks import AfterNodeCallEvent, BeforeNodeCallEvent, HookProvider

    class Hook(HookProvider):
        def __init__(self):
            self.after_count = 0

        def register_hooks(self, registry):
            registry.add_callback(BeforeNodeCallEvent, self.interrupt)
            registry.add_callback(AfterNodeCallEvent, self.cleanup)

        def interrupt(self, event):
            return event.interrupt("test_name", reason="test_reason")

        def cleanup(self, event):
            self.after_count += 1

    return Hook()


@pytest.mark.asyncio
async def test_after_node_call_event_not_emitted_on_interrupt(interrupt_hook):
    """
    Test that AfterNodeCallEvent is NOT emitted when a node is interrupted during execution.

    This test exercises the multi-agent graph execution with an interrupt hook that interrupts
    the node before execution. It verifies that the AfterNodeCallEvent callback is not invoked in this case,
    matching the expected behavior after the fix.

    The test uses the interrupt_hook fixture which interrupts nodes on BeforeNodeCallEvent and counts
    AfterNodeCallEvent invocations.
    """
    from strands.multiagent.graph import GraphBuilder, Status
    from strands.agent import Agent

    # Create a simple agent that returns a fixed response
    class SimpleAgent(Agent):
        def __init__(self):
            super().__init__()
            self.name = "simple_agent"
            self.id = "simple_agent"

        async def invoke_async(self, input_data, invocation_state=None):
            return self.return_value

        async def stream_async(self, input_data, **kwargs):
            yield {"agent_start": True}
            yield {"result": self.return_value}

    agent = SimpleAgent()
    from strands.agent import AgentResult
    agent.return_value = AgentResult(
        message={"role": "assistant", "content": [{"text": "Hello"}]},
        stop_reason="end_turn",
        state={},
        metrics={},
    )

    builder = GraphBuilder()
    builder.add_node(agent, "simple_agent")
    builder.set_entry_point("simple_agent")
    builder.set_hook_providers([interrupt_hook])
    graph = builder.build()

    result = graph("Test task")

    # The interrupt_hook should have interrupted the node, so status should be INTERRUPTED
    assert result.status == Status.INTERRUPTED

    # AfterNodeCallEvent should NOT have been called due to interrupt
    assert interrupt_hook.after_count == 0


@pytest.mark.asyncio
async def test_after_node_call_event_not_emitted_on_interrupt_swarm(interrupt_hook):
    """
    Test that AfterNodeCallEvent is NOT emitted when a swarm node is interrupted during execution.

    This test exercises the multi-agent swarm execution with an interrupt hook that interrupts
    the node before execution. It verifies that the AfterNodeCallEvent callback is not invoked in this case,
    matching the expected behavior after the fix.

    The test uses the interrupt_hook fixture which interrupts nodes on BeforeNodeCallEvent and counts
    AfterNodeCallEvent invocations.
    """
    from strands.multiagent.swarm import Swarm
    from strands.agent import Agent
    from strands.multiagent.base import Status

    # Create a simple agent that returns a fixed response
    class SimpleAgent(Agent):
        def __init__(self):
            super().__init__()
            self.name = "simple_agent"
            self.id = "simple_agent"

        async def invoke_async(self, input_data, invocation_state=None):
            return self.return_value

        async def stream_async(self, input_data, **kwargs):
            yield {"agent_start": True}
            yield {"result": self.return_value}

    agent = SimpleAgent()
    from strands.agent import AgentResult
    agent.return_value = AgentResult(
        message={"role": "assistant", "content": [{"text": "Hello"}]},
        stop_reason="end_turn",
        state={},
        metrics={},
    )

    swarm = Swarm([agent], hooks=[interrupt_hook])

    result = swarm("Test task")

    # The interrupt_hook should have interrupted the node, so status should be INTERRUPTED
    assert result.status == Status.INTERRUPTED

    # AfterNodeCallEvent should NOT have been called due to interrupt
    assert interrupt_hook.after_count == 0
