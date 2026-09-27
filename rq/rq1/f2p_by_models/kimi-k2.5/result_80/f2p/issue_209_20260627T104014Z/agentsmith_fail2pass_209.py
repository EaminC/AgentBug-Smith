from dapr_agents.agents.orchestrators.base import OrchestratorBase


def test_final_summary_callback_mechanism():
    """
    Test that final_summary_callback parameter is accepted and invoked.
    
    Verifies the fix for issue #209 - workflow completion callback capabilities.
    On buggy code: TypeError on __init__ (unexpected keyword argument) or 
    AttributeError on _invoke_final_summary_callback.
    On fixed code: Callback is stored and invoked correctly.
    """
    callback_invoked = []
    
    def my_callback(summary: str) -> None:
        callback_invoked.append(summary)
    
    # Verify constructor accepts final_summary_callback parameter (fix adds this)
    orchestrator = OrchestratorBase(
        name="test_orchestrator",
        final_summary_callback=my_callback
    )
    
    # Verify the callback is stored as _final_summary_callback (fix adds this)
    assert hasattr(orchestrator, '_final_summary_callback')
    assert orchestrator._final_summary_callback is my_callback
    
    # Verify _invoke_final_summary_callback method exists and invokes the callback (fix adds this)
    assert hasattr(orchestrator, '_invoke_final_summary_callback')
    orchestrator._invoke_final_summary_callback("workflow completed successfully")
    
    # Verify the callback was actually called with the correct argument
    assert len(callback_invoked) == 1
    assert callback_invoked[0] == "workflow completed successfully"
