import pytest

from strands.agent.agent_result import AgentResult
from strands.telemetry.metrics import EventLoopMetrics, Usage


def test_agent_result_context_size_property_delegates_to_metrics():
    class DummyMetrics:
        latest_context_size = 42

    dummy_metrics = DummyMetrics()
    result = AgentResult(
        stop_reason="end_turn",
        message={"role": "assistant", "content": [{"text": "Hello"}]},
        metrics=dummy_metrics,
        state={},
    )
    assert result.context_size == 42


def test_agent_result_context_size_property_none_when_metrics_none():
    class DummyMetrics:
        latest_context_size = None

    dummy_metrics = DummyMetrics()
    result = AgentResult(
        stop_reason="end_turn",
        message={"role": "assistant", "content": [{"text": "Hello"}]},
        metrics=dummy_metrics,
        state={},
    )
    assert result.context_size is None


def test_event_loop_metrics_latest_context_size_none_when_no_invocations():
    metrics = EventLoopMetrics()
    # No invocations at all
    assert metrics.latest_context_size is None


def test_event_loop_metrics_latest_context_size_none_when_invocation_no_cycles():
    metrics = EventLoopMetrics()
    metrics.reset_usage_metrics()  # creates an invocation with no cycles
    assert metrics.latest_context_size is None


def test_event_loop_metrics_latest_context_size_returns_last_cycle_input_tokens():
    metrics = EventLoopMetrics()
    metrics.reset_usage_metrics()
    metrics.start_cycle(attributes={"event_loop_cycle_id": "cycle1"})
    metrics.update_usage(Usage(inputTokens=100, outputTokens=50, totalTokens=150))
    metrics.start_cycle(attributes={"event_loop_cycle_id": "cycle2"})
    metrics.update_usage(Usage(inputTokens=250, outputTokens=80, totalTokens=330))
    # The latest context size should be inputTokens of last cycle (250)
    assert metrics.latest_context_size == 250


def test_event_loop_metrics_latest_context_size_returns_latest_invocation_last_cycle():
    metrics = EventLoopMetrics()
    # First invocation
    metrics.reset_usage_metrics()
    metrics.start_cycle(attributes={"event_loop_cycle_id": "cycle1"})
    metrics.update_usage(Usage(inputTokens=100, outputTokens=50, totalTokens=150))
    # Second invocation
    metrics.reset_usage_metrics()
    metrics.start_cycle(attributes={"event_loop_cycle_id": "cycle2"})
    metrics.update_usage(Usage(inputTokens=500, outputTokens=80, totalTokens=580))
    assert metrics.latest_context_size == 500


def test_event_loop_metrics_latest_context_size_returns_none_if_input_tokens_missing():
    metrics = EventLoopMetrics()
    metrics.reset_usage_metrics()
    invocation = metrics.agent_invocations[-1]
    # Append a cycle with usage missing inputTokens key
    invocation.cycles.append(
        type(
            "Cycle",
            (),
            {"usage": {"outputTokens": 10, "totalTokens": 10}},
        )()
    )
    assert metrics.latest_context_size is None
