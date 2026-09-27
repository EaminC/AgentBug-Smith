from crewai.flow.flow import Flow, listen, router, start


def test_multiple_routers_trigger_all_listeners():
    """Test that when multiple routers are triggered by the same method,
    all their respective listeners are executed, not just the last one."""
    execution_order = []

    class MultiRouterFlow(Flow):
        def __init__(self):
            super().__init__()
            # Set conditions so that all three routers return a path
            self.state["conditions"] = "ABC"

        @start()
        def step_one(self):
            execution_order.append("step_one")

        @router(step_one)
        def router_a(self):
            execution_order.append("router_a")
            if "A" in self.state["conditions"]:
                return "path_a"
            return None

        @listen("path_a")
        def listener_a(self):
            execution_order.append("listener_a")

        @router(step_one)
        def router_b(self):
            execution_order.append("router_b")
            if "B" in self.state["conditions"]:
                return "path_b"
            return None

        @listen("path_b")
        def listener_b(self):
            execution_order.append("listener_b")

        @router(step_one)
        def router_c(self):
            execution_order.append("router_c")
            if "C" in self.state["conditions"]:
                return "path_c"
            return None

        @listen("path_c")
        def listener_c(self):
            execution_order.append("listener_c")

    flow = MultiRouterFlow()
    flow.kickoff()

    # All routers should be executed
    assert "router_a" in execution_order
    assert "router_b" in execution_order
    assert "router_c" in execution_order

    # All listeners should be executed – this is the key assertion that fails before the fix
    assert "listener_a" in execution_order
    assert "listener_b" in execution_order
    assert "listener_c" in execution_order

    # Verify ordering: listeners come after their respective routers
    assert execution_order.index("listener_a") > execution_order.index("router_a")
    assert execution_order.index("listener_b") > execution_order.index("router_b")
    assert execution_order.index("listener_c") > execution_order.index("router_c")
