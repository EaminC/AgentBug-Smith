import pytest

from strands.types.event_loop import Usage
from strands.telemetry.metrics import EventLoopMetrics


@pytest.mark.parametrize(
    "usages, expected_accumulated",
    [
        (
            [
                Usage(inputTokens=1, outputTokens=2, totalTokens=3, cacheReadInputTokens=4, cacheWriteInputTokens=5),
                Usage(inputTokens=10, outputTokens=20, totalTokens=30, cacheReadInputTokens=40, cacheWriteInputTokens=50),
            ],
            Usage(inputTokens=11, outputTokens=22, totalTokens=33, cacheReadInputTokens=44, cacheWriteInputTokens=55),
        ),
        (
            [
                Usage(inputTokens=0, outputTokens=0, totalTokens=0),
                Usage(inputTokens=5, outputTokens=5, totalTokens=10, cacheReadInputTokens=1),
            ],
            Usage(inputTokens=5, outputTokens=5, totalTokens=10, cacheReadInputTokens=1),
        ),
        (
            [
                Usage(inputTokens=3, outputTokens=3, totalTokens=6, cacheWriteInputTokens=7),
                Usage(inputTokens=2, outputTokens=2, totalTokens=4),
            ],
            Usage(inputTokens=5, outputTokens=5, totalTokens=10, cacheWriteInputTokens=7),
        ),
    ],
)
def test_event_loop_metrics_accumulates_cached_tokens(usages, expected_accumulated):
    metrics = EventLoopMetrics()
    for usage in usages:
        metrics.update_usage(usage)

    # The accumulated_usage should match the sum of all usages including cached tokens
    for key in expected_accumulated:
        assert metrics.accumulated_usage.get(key, 0) == expected_accumulated[key]


def test_event_loop_metrics_records_cache_token_metrics(monkeypatch):
    recorded = {"cache_read": [], "cache_write": []}

    class DummyHistogram:
        def record(self, value):
            if value == 0:
                # ignore zero for test clarity
                return
            # We cannot rely on str(value) containing 'cache_read' or 'cache_write' because value is int
            # Instead, we record all calls separately by monkeypatching the two histograms
            # So here just append value to a generic list
            recorded["called"].append(value)

    metrics = EventLoopMetrics()
    # monkeypatch the histograms to capture calls
    recorded["called"] = []
    metrics._metrics_client.event_loop_cache_read_input_tokens = DummyHistogram()
    metrics._metrics_client.event_loop_cache_write_input_tokens = DummyHistogram()

    # Provide usage with cache tokens
    usage = Usage(inputTokens=1, outputTokens=2, totalTokens=3, cacheReadInputTokens=7, cacheWriteInputTokens=11)
    metrics.update_usage(usage)

    # The accumulated_usage should include the cache tokens
    assert metrics.accumulated_usage["cacheReadInputTokens"] == 7
    assert metrics.accumulated_usage["cacheWriteInputTokens"] == 11

    # The histograms should have recorded the values
    # Since both histograms use the same DummyHistogram instance, recorded["called"] should contain both values
    assert 7 in recorded["called"]
    assert 11 in recorded["called"]


def test_metrics_summary_includes_cache_tokens():
    metrics = EventLoopMetrics()
    # Set accumulated_usage with cache tokens
    metrics.accumulated_usage = Usage(
        inputTokens=10,
        outputTokens=20,
        totalTokens=30,
        cacheReadInputTokens=40,
        cacheWriteInputTokens=50,
    )
    metrics.accumulated_metrics = {"latencyMs": 123}
    metrics.cycle_count = 1
    metrics.cycle_durations = [1.0]
    metrics.total_duration = 1.0

    # The function _metrics_summary_to_lines is a standalone function in strands.telemetry.metrics module
    # We import it here for the test
    from strands.telemetry.metrics import _metrics_summary_to_lines

    summary_lines = list(_metrics_summary_to_lines(metrics, allowed_names=None))

    # The summary lines should include the cached token metrics
    tokens_line = next((line for line in summary_lines if line.startswith("├─ Tokens:")), None)
    assert tokens_line is not None
    assert "cache_read_input_tokens=40" in tokens_line
    assert "cache_write_input_tokens=50" in tokens_line

    # Also check other expected lines exist
    assert any(line.startswith("├─ Cycles:") for line in summary_lines)
    assert any(line.startswith("├─ Bedrock Latency:") for line in summary_lines)
    assert any(line.startswith("├─ Tool Usage:") for line in summary_lines)
