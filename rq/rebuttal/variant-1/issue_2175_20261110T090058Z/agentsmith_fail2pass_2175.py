from crewai.flow.flow import Flow, start, router, listen


def test_multiple_routers_trigger_all_listeners():
    """
    Test that multiple routers triggered by the same method all activate their listeners.
    This test reproduces the bug where only the last router triggers events.
    After the fix, all routers should trigger their respective listeners.
    """

    execution_order = []

    class MedicalFlow(Flow):
        def __init__(self):
            super().__init__()
            # Setup state to simulate diagnosed conditions triggering all routers
            self.state["diagnosed_conditions"] = "DHA"  # D: Diabetes, H: Hypertension, A: Anemia

        @start()
        def scan_medical(self):
            execution_order.append("scan_medical")
            return "scan_complete"

        @router(scan_medical)
        def diagnose_conditions(self):
            execution_order.append("diagnose_conditions")
            return "diagnosis_complete"

        @router(diagnose_conditions)
        def diabetes_router(self):
            execution_order.append("diabetes_router")
            if "D" in self.state["diagnosed_conditions"]:
                return "diabetes"
            return None

        @listen("diabetes")
        def diabetes_analysis(self):
            execution_order.append("diabetes_analysis")
            return "diabetes_analysis_done"

        @router(diagnose_conditions)
        def hypertension_router(self):
            execution_order.append("hypertension_router")
            if "H" in self.state["diagnosed_conditions"]:
                return "hypertension"
            return None

        @listen("hypertension")
        def hypertension_analysis(self):
            execution_order.append("hypertension_analysis")
            return "hypertension_analysis_done"

        @router(diagnose_conditions)
        def anemia_router(self):
            execution_order.append("anemia_router")
            if "A" in self.state["diagnosed_conditions"]:
                return "anemia"
            return None

        @listen("anemia")
        def anemia_analysis(self):
            execution_order.append("anemia_analysis")
            return "anemia_analysis_done"

    flow = MedicalFlow()
    flow.kickoff()

    # Check that all main steps were executed
    assert "scan_medical" in execution_order
    assert "diagnose_conditions" in execution_order

    # Check that all routers were executed
    assert "diabetes_router" in execution_order
    assert "hypertension_router" in execution_order
    assert "anemia_router" in execution_order

    # Check that all listeners were executed (key test for the fix)
    assert "diabetes_analysis" in execution_order
    assert "hypertension_analysis" in execution_order
    assert "anemia_analysis" in execution_order

    # Check execution order constraints
    # diagnose_conditions must happen after scan_medical
    assert execution_order.index("diagnose_conditions") > execution_order.index("scan_medical")

    # All routers must execute after diagnose_conditions
    assert execution_order.index("diabetes_router") > execution_order.index("diagnose_conditions")
    assert execution_order.index("hypertension_router") > execution_order.index("diagnose_conditions")
    assert execution_order.index("anemia_router") > execution_order.index("diagnose_conditions")

    # Each analysis must execute after its router
    assert execution_order.index("diabetes_analysis") > execution_order.index("diabetes_router")
    assert execution_order.index("hypertension_analysis") > execution_order.index("hypertension_router")
    assert execution_order.index("anemia_analysis") > execution_order.index("anemia_router")
