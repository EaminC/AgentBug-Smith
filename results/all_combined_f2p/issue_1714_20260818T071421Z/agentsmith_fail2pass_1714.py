import inspect
import pytest
from typing import Union

from strands.agent.agent import Agent
from strands.hooks.events import (
    AfterModelCallEvent,
    BeforeModelCallEvent,
)
from strands.hooks.registry import HookRegistry


def test_agent_add_hook_with_union_type_registers_for_all_types():
    """Test that agent.add_hook registers callback for each event type in union type hint."""

    agent = Agent()
    call_counts = {BeforeModelCallEvent: 0, AfterModelCallEvent: 0}

    def union_hook(event: BeforeModelCallEvent | AfterModelCallEvent) -> None:
        call_counts[type(event)] += 1

    agent.add_hook(union_hook)

    # The callback should be registered for both event types
    registry: HookRegistry = agent.hooks
    assert BeforeModelCallEvent in registry._registered_callbacks
    assert AfterModelCallEvent in registry._registered_callbacks
    assert union_hook in registry._registered_callbacks[BeforeModelCallEvent]
    assert union_hook in registry._registered_callbacks[AfterModelCallEvent]

    # Invoke callbacks to verify they are called correctly
    before_event = BeforeModelCallEvent(agent=agent)
    after_event = AfterModelCallEvent(agent=agent)

    # Use async invoke_callbacks_async to trigger callbacks
    import asyncio

    async def invoke_all():
        await registry.invoke_callbacks_async(before_event)
        await registry.invoke_callbacks_async(after_event)

    asyncio.run(invoke_all())

    assert call_counts[BeforeModelCallEvent] == 1
    assert call_counts[AfterModelCallEvent] == 1


def test_agent_add_hook_with_list_of_types_registers_for_all_types():
    """Test that agent.add_hook registers callback for each event type in list parameter."""

    agent = Agent()
    call_counts = {BeforeModelCallEvent: 0, AfterModelCallEvent: 0}

    def list_hook(event) -> None:
        call_counts[type(event)] += 1

    agent.add_hook(list_hook, [BeforeModelCallEvent, AfterModelCallEvent])

    registry: HookRegistry = agent.hooks
    assert BeforeModelCallEvent in registry._registered_callbacks
    assert AfterModelCallEvent in registry._registered_callbacks
    assert list_hook in registry._registered_callbacks[BeforeModelCallEvent]
    assert list_hook in registry._registered_callbacks[AfterModelCallEvent]

    # Invoke callbacks to verify they are called correctly
    before_event = BeforeModelCallEvent(agent=agent)
    after_event = AfterModelCallEvent(agent=agent)

    import asyncio

    async def invoke_all():
        await registry.invoke_callbacks_async(before_event)
        await registry.invoke_callbacks_async(after_event)

    asyncio.run(invoke_all())

    assert call_counts[BeforeModelCallEvent] == 1
    assert call_counts[AfterModelCallEvent] == 1


def test_agent_add_hook_with_list_of_types_deduplicates():
    """Test that agent.add_hook deduplicates event types in the list parameter."""

    agent = Agent()
    call_counts = {BeforeModelCallEvent: 0, AfterModelCallEvent: 0}

    def list_hook(event) -> None:
        call_counts[type(event)] += 1

    # Duplicate BeforeModelCallEvent in list
    agent.add_hook(list_hook, [BeforeModelCallEvent, BeforeModelCallEvent, AfterModelCallEvent])

    registry: HookRegistry = agent.hooks
    # Callback should be registered only once per event type
    # There may be other callbacks registered for BeforeModelCallEvent by default agent hooks,
    # so we check that our callback is present and count duplicates of our callback only.
    callbacks_before = registry._registered_callbacks.get(BeforeModelCallEvent, [])
    callbacks_after = registry._registered_callbacks.get(AfterModelCallEvent, [])

    # Count how many times list_hook appears in each event type callbacks
    count_before = sum(1 for cb in callbacks_before if cb == list_hook)
    count_after = sum(1 for cb in callbacks_after if cb == list_hook)

    assert count_before == 1
    assert count_after == 1

    # Invoke callbacks to verify they are called correctly
    before_event = BeforeModelCallEvent(agent=agent)
    after_event = AfterModelCallEvent(agent=agent)

    import asyncio

    async def invoke_all():
        await registry.invoke_callbacks_async(before_event)
        await registry.invoke_callbacks_async(after_event)

    asyncio.run(invoke_all())

    assert call_counts[BeforeModelCallEvent] == 1
    assert call_counts[AfterModelCallEvent] == 1


def test_agent_add_hook_with_union_type_containing_none_raises():
    """Test that agent.add_hook raises ValueError if union type hint contains None."""

    agent = Agent()

    def callback_with_none(event: BeforeModelCallEvent | None) -> None:
        pass

    with pytest.raises(ValueError, match="None is not a valid event type"):
        agent.add_hook(callback_with_none)


def test_agent_add_hook_with_union_type_containing_invalid_type_raises():
    """Test that agent.add_hook raises ValueError if union type hint contains invalid type."""

    agent = Agent()

    def callback_with_invalid(event: BeforeModelCallEvent | str) -> None:
        pass

    with pytest.raises(ValueError, match="Invalid type in union"):
        agent.add_hook(callback_with_invalid)


def test_agent_add_hook_signature_no_kwargs():
    """Test that agent.add_hook does not accept **kwargs parameter."""

    sig = inspect.signature(Agent.add_hook)
    params = sig.parameters

    # The parameter list should NOT contain **kwargs
    for p in params.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD, "add_hook should not accept **kwargs"
