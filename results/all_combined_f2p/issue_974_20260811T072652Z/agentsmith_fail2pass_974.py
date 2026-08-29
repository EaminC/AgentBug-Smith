import pytest
from src.agentscope.agent import _react_agent as react_agent_module


class DummyTool:
    def __init__(self, name):
        self.name = name

    def __call__(self):
        return f"Tool {self.name} called"


class DummyPlanNotebook:
    def __init__(self):
        self.description = "Dummy plan notebook description"
        self.tools = [DummyTool("tool1"), DummyTool("tool2")]

    def list_tools(self):
        return self.tools


class DummyToolkit:
    def __init__(self):
        self.registered_functions = []
        self.created_tool_groups = {}
        self.reset_equipped_tools = lambda: "reset_equipped_tools called"

    def register_tool_function(self, func, group_name=None):
        self.registered_functions.append((func, group_name))

    def create_tool_group(self, group_name, description=None):
        self.created_tool_groups[group_name] = description


@pytest.mark.parametrize(
    "enable_meta_tool, plan_notebook, expect_reset_registered, expect_plan_group_created",
    [
        (True, None, True, False),
        (False, None, False, False),
        (True, DummyPlanNotebook(), True, True),
        (False, DummyPlanNotebook(), False, False),
    ],
)
def test_reset_equipped_tools_registration_and_plan_group_creation(
    enable_meta_tool, plan_notebook, expect_reset_registered, expect_plan_group_created
):
    """
    This test verifies that:
    - The reset_equipped_tools function is registered only if enable_meta_tool is True.
    - The "plan_related" tool group is created only if enable_meta_tool is True and plan_notebook is provided.
    - When enable_meta_tool is False but plan_notebook is provided, reset_equipped_tools is NOT registered,
      and no "plan_related" group is created.
    """

    # We create a minimal subclass of ReActAgent that accepts the parameters we want
    # and uses DummyToolkit to track registrations.
    class TestReactAgent(react_agent_module.ReActAgent):
        def __init__(self):
            # The real ReActAgent __init__ requires name, sys_prompt, model, formatter.
            # Provide dummy values for those.
            # We pass our DummyToolkit instance to track registrations.
            dummy_toolkit = DummyToolkit()
            super().__init__(
                name="test_agent",
                sys_prompt="test prompt",
                model="test_model",
                formatter="test_formatter",
                toolkit=dummy_toolkit,
                knowledge=None,
                enable_meta_tool=enable_meta_tool,
                plan_notebook=plan_notebook,
                enable_rewrite_query=False,
                parallel_tool_calls=False,
            )
            # Replace toolkit with dummy toolkit to track calls
            self.toolkit = dummy_toolkit

    agent = TestReactAgent()

    # Check if reset_equipped_tools is registered
    reset_registered = any(
        func == agent.toolkit.reset_equipped_tools for func, _ in agent.toolkit.registered_functions
    )
    assert reset_registered == expect_reset_registered, (
        f"reset_equipped_tools registration expected={expect_reset_registered} but got {reset_registered}"
    )

    # Check if "plan_related" tool group is created
    plan_group_created = "plan_related" in agent.toolkit.created_tool_groups
    assert plan_group_created == expect_plan_group_created, (
        f"'plan_related' tool group creation expected={expect_plan_group_created} but got {plan_group_created}"
    )

    # Additional check: if plan_notebook is provided and enable_meta_tool is False,
    # the plan tools should be registered without group_name.
    if plan_notebook and not enable_meta_tool:
        registered_tools = [func for func, group in agent.toolkit.registered_functions if func != agent.toolkit.reset_equipped_tools]
        expected_tools = plan_notebook.list_tools()
        # Check all expected tools are registered without group_name
        for tool in expected_tools:
            found = any((func == tool and group is None) for func, group in agent.toolkit.registered_functions)
            assert found, f"Expected tool {tool.name} to be registered without group_name when enable_meta_tool=False"


# Run the test if this file is executed directly
if __name__ == "__main__":
    import sys
    import pytest

    sys.exit(pytest.main([__file__]))
