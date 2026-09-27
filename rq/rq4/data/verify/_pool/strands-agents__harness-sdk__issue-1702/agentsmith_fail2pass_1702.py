import threading

import pytest

from strands.agent import Agent
from strands.types.agent import ConcurrentInvocationMode
from strands.types.exceptions import ConcurrencyException
from tests.fixtures.mocked_model_provider import MockedModelProvider


class SyncEventMockedModel(MockedModelProvider):
    """A mock model that uses events to synchronize concurrent threads.

    This model signals when it starts streaming and waits for a proceed signal,
    allowing deterministic testing of concurrent behavior without relying on sleeps.
    """

    def __init__(self, agent_responses):
        super().__init__(agent_responses)
        self.started_event = threading.Event()
        self.proceed_event = threading.Event()

    async def stream(
        self, messages, tool_specs=None, system_prompt=None, tool_choice=None, **kwargs
    ):
        # Signal that streaming has started
        self.started_event.set()
        # Wait for signal to proceed
        self.proceed_event.wait()
        async for event in super().stream(messages, tool_specs, system_prompt, tool_choice, **kwargs):
            yield event


def test_agent_concurrent_call_succeeds_with_unsafe_reentrant_mode():
    """Test that concurrent __call__() calls succeed when concurrent_invocation_mode is 'unsafe_reentrant'."""
    model = SyncEventMockedModel(
        [
            {"role": "assistant", "content": [{"text": "hello"}]},
            {"role": "assistant", "content": [{"text": "world"}]},
        ]
    )
    agent = Agent(model=model, concurrent_invocation_mode="unsafe_reentrant")

    results = []
    errors = []
    lock = threading.Lock()

    def invoke():
        try:
            result = agent("test")
            with lock:
                results.append(result)
        except ConcurrencyException as e:
            with lock:
                errors.append(e)

    # Start first thread and wait for it to begin streaming
    t1 = threading.Thread(target=invoke)
    t1.start()
    model.started_event.wait()  # Wait until first thread is in the model.stream()

    # Start second thread while first is still running
    t2 = threading.Thread(target=invoke)
    t2.start()

    # Let both threads proceed
    model.proceed_event.set()
    t1.join()
    t2.join()

    # Both should succeed, no ConcurrencyException raised
    assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}: {errors}"
    assert len(results) == 2, f"Expected 2 successes, got {len(results)}"


def test_agent_concurrent_call_raises_exception_by_default():
    """Test that concurrent __call__() calls raise ConcurrencyException by default (mode 'throw')."""
    model = SyncEventMockedModel(
        [
            {"role": "assistant", "content": [{"text": "hello"}]},
            {"role": "assistant", "content": [{"text": "world"}]},
        ]
    )
    agent = Agent(model=model)  # default mode is "throw"

    results = []
    errors = []

    def invoke():
        try:
            result = agent("test")
            results.append(result)
        except ConcurrencyException as e:
            errors.append(e)

    # Start first thread and wait for it to begin streaming
    t1 = threading.Thread(target=invoke)
    t1.start()
    model.started_event.wait()  # Wait until first thread is in the model.stream()

    # Start second thread while first is still running
    t2 = threading.Thread(target=invoke)
    t2.start()

    # Give second thread time to attempt invocation and fail
    t2.join(timeout=1.0)

    # Now let first thread complete
    model.proceed_event.set()
    t1.join()
    t2.join()

    # One should succeed, one should raise ConcurrencyException
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
    assert "concurrent" in str(errors[0]).lower() and "invocation" in str(errors[0]).lower()


def test_agent_concurrent_invocation_mode_default_is_throw():
    """Test that the default concurrent_invocation_mode is 'throw'."""
    model = MockedModelProvider([{"role": "assistant", "content": [{"text": "hello"}]}])
    agent = Agent(model=model)

    # Verify the default mode
    assert agent._concurrent_invocation_mode == "throw"


def test_agent_concurrent_invocation_mode_stores_value():
    """Test that concurrent_invocation_mode is stored correctly as instance variable."""
    model = MockedModelProvider([{"role": "assistant", "content": [{"text": "hello"}]}])

    agent_throw = Agent(model=model, concurrent_invocation_mode="throw")
    assert agent_throw._concurrent_invocation_mode == "throw"

    agent_reentrant = Agent(model=model, concurrent_invocation_mode="unsafe_reentrant")
    assert agent_reentrant._concurrent_invocation_mode == "unsafe_reentrant"


def test_agent_concurrent_invocation_mode_accepts_enum():
    """Test that concurrent_invocation_mode accepts enum values as well as strings."""

    model = MockedModelProvider([{"role": "assistant", "content": [{"text": "hello"}]}])

    # Using enum values
    agent_throw = Agent(model=model, concurrent_invocation_mode=ConcurrentInvocationMode.THROW)
    assert agent_throw._concurrent_invocation_mode == "throw"
    assert agent_throw._concurrent_invocation_mode == ConcurrentInvocationMode.THROW

    agent_reentrant = Agent(model=model, concurrent_invocation_mode=ConcurrentInvocationMode.UNSAFE_REENTRANT)
    assert agent_reentrant._concurrent_invocation_mode == "unsafe_reentrant"
    assert agent_reentrant._concurrent_invocation_mode == ConcurrentInvocationMode.UNSAFE_REENTRANT
