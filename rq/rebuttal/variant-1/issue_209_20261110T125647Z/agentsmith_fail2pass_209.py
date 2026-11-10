import threading
import pytest

from dapr_agents.agents.orchestrators.base import OrchestratorBase
from dapr_agents.agents.orchestrators.random import RandomOrchestrator
from dapr_agents.agents.orchestrators.roundrobin import RoundRobinOrchestrator


def test_workflow_completion_callback_invoked():
    """
    Test that the onWorkflowCompletion callback is invoked with the final workflow result.

    This test creates orchestrators with a callback that stores the final summary.
    It simulates running a workflow that completes immediately with a known result.
    The test asserts that the callback was called and received the expected result.

    Fail2pass criteria:
    - On the buggy codebase, the callback is not invoked, so the test fails.
    - After the fix, the callback is invoked, and the test passes.
    """

    callback_called = threading.Event()
    callback_result = {}

    def on_workflow_completion(summary: str) -> None:
        callback_result["summary"] = summary
        callback_called.set()

    # Helper: simulate a workflow run that calls the callback with a known summary.
    def simulate_run(orchestrator: OrchestratorBase, final_output: str):
        # Directly invoke the internal callback method to simulate completion.
        orchestrator._invoke_final_summary_callback(final_output)

    # We test RandomOrchestrator and RoundRobinOrchestrator because OrchestratorBase itself
    # does not accept final_summary_callback directly (constructor signature).
    # So we instantiate RandomOrchestrator and RoundRobinOrchestrator with the callback.

    # Test RandomOrchestrator
    random_orchestrator = RandomOrchestrator.__new__(RandomOrchestrator)
    # Manually initialize base class with callback
    OrchestratorBase.__init__(
        random_orchestrator,
        name="test-random-orchestrator",
        pubsub=None,
        state=None,
        registry=None,
        agent_metadata=None,
        workflow_grpc=None,
        runtime=None,
        workflow_client=None,
        default_bundle=None,
        final_summary_callback=on_workflow_completion,
    )

    # Simulate a workflow run with a known final output
    test_summary = "random final output"
    simulate_run(random_orchestrator, test_summary)

    # Wait for callback to be called
    assert callback_called.wait(timeout=1), "Callback was not called for RandomOrchestrator"
    assert callback_result.get("summary") == test_summary

    # Reset for RoundRobinOrchestrator
    callback_called.clear()
    callback_result.clear()

    # Test RoundRobinOrchestrator
    roundrobin_orchestrator = RoundRobinOrchestrator.__new__(RoundRobinOrchestrator)
    OrchestratorBase.__init__(
        roundrobin_orchestrator,
        name="test-roundrobin-orchestrator",
        pubsub=None,
        state=None,
        registry=None,
        agent_metadata=None,
        workflow_grpc=None,
        runtime=None,
        workflow_client=None,
        default_bundle=None,
        final_summary_callback=on_workflow_completion,
    )

    test_summary_rr = "roundrobin final output"
    simulate_run(roundrobin_orchestrator, test_summary_rr)

    assert callback_called.wait(timeout=1), "Callback was not called for RoundRobinOrchestrator"
    assert callback_result.get("summary") == test_summary_rr
