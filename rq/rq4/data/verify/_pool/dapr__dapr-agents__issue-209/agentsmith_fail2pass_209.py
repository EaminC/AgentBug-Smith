import pytest
from unittest.mock import Mock
from dapr_agents.agents.orchestrators.base import OrchestratorBase


class TestFinalSummaryCallback:
    """Test that final_summary_callback is properly invoked on workflow completion."""

    def test_orchestrator_base_accepts_final_summary_callback(self):
        """Test that OrchestratorBase accepts final_summary_callback parameter."""
        callback = Mock()
        
        orchestrator = OrchestratorBase(
            name="test_orchestrator",
            final_summary_callback=callback
        )
        
        assert orchestrator._final_summary_callback is callback

    def test_invoke_final_summary_callback_calls_callback(self):
        """Test that _invoke_final_summary_callback properly invokes the callback."""
        callback = Mock()
        
        orchestrator = OrchestratorBase(
            name="test_orchestrator",
            final_summary_callback=callback
        )
        
        test_summary = "Test workflow summary"
        orchestrator._invoke_final_summary_callback(test_summary)
        
        callback.assert_called_once_with(test_summary)

    def test_invoke_final_summary_callback_handles_exception(self):
        """Test that _invoke_final_summary_callback handles callback exceptions gracefully."""
        callback = Mock(side_effect=Exception("Callback error"))
        
        orchestrator = OrchestratorBase(
            name="test_orchestrator",
            final_summary_callback=callback
        )
        
        test_summary = "Test workflow summary"
        
        orchestrator._invoke_final_summary_callback(test_summary)
        
        callback.assert_called_once_with(test_summary)

    def test_invoke_final_summary_callback_with_none_callback(self):
        """Test that _invoke_final_summary_callback handles None callback gracefully."""
        orchestrator = OrchestratorBase(
            name="test_orchestrator",
            final_summary_callback=None
        )
        
        test_summary = "Test workflow summary"
        
        orchestrator._invoke_final_summary_callback(test_summary)

    def test_invoke_final_summary_callback_with_no_callback_parameter(self):
        """Test that _invoke_final_summary_callback works when callback not provided."""
        orchestrator = OrchestratorBase(
            name="test_orchestrator"
        )
        
        test_summary = "Test workflow summary"
        
        orchestrator._invoke_final_summary_callback(test_summary)

    def test_callback_receives_final_summary_string(self):
        """Test that callback receives the final summary as a string."""
        received_summary = None
        
        def capture_summary(summary: str):
            nonlocal received_summary
            received_summary = summary
        
        orchestrator = OrchestratorBase(
            name="test_orchestrator",
            final_summary_callback=capture_summary
        )
        
        test_summary = "This is the final workflow summary"
        orchestrator._invoke_final_summary_callback(test_summary)
        
        assert received_summary == test_summary

    def test_callback_is_optional(self):
        """Test that callback parameter is optional and doesn't break initialization."""
        orchestrator1 = OrchestratorBase(name="test1")
        orchestrator2 = OrchestratorBase(name="test2", final_summary_callback=None)
        
        assert orchestrator1._final_summary_callback is None
        assert orchestrator2._final_summary_callback is None

    def test_method_invoke_final_summary_callback_exists(self):
        """Test that _invoke_final_summary_callback method exists on OrchestratorBase."""
        orchestrator = OrchestratorBase(name="test_orchestrator")
        
        assert hasattr(orchestrator, "_invoke_final_summary_callback")
        assert callable(getattr(orchestrator, "_invoke_final_summary_callback"))
