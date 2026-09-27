import sys
import types
from pathlib import Path
from unittest.mock import MagicMock
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec

# ---------------------------------------------------------------------------
# 1. Dynamic Mock Package for MCP
# ---------------------------------------------------------------------------
class MockMCPModule(types.ModuleType):
    """Module mock that pretends to be a package and returns mocks for any attribute."""
    def __init__(self, name: str):
        super().__init__(name)
        self.__path__ = []

    def __getattr__(self, name: str):
        val = MagicMock()
        setattr(self, name, val)
        return val


class MockMCPFinder(MetaPathFinder, Loader):
    """Intercepts all imports under 'mcp' or 'mcp.*'."""
    def find_spec(self, fullname, path, target=None):
        if fullname == "mcp" or fullname.startswith("mcp."):
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        mod = MockMCPModule(spec.name)
        mod.__loader__ = self
        mod.__spec__ = spec
        return mod

    def exec_module(self, module):
        pass


# Purge any existing partial mcp modules from sys.modules and install finder
for k in list(sys.modules.keys()):
    if k == "mcp" or k.startswith("mcp."):
        sys.modules.pop(k, None)

sys.meta_path.insert(0, MockMCPFinder())

# ---------------------------------------------------------------------------
# 2. Path Setup & Module Import
# ---------------------------------------------------------------------------
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest

try:
    from agentscope.agent import _react_agent as react_agent_module
except ImportError:
    from src.agentscope.agent import _react_agent as react_agent_module


# ---------------------------------------------------------------------------
# 3. Test Fixtures & Assertions
# ---------------------------------------------------------------------------
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
    Verifies that:
    - reset_equipped_tools is registered only if enable_meta_tool is True.
    - The "plan_related" tool group is created only if enable_meta_tool is True and plan_notebook is provided.
    - When enable_meta_tool is False but plan_notebook is provided, reset_equipped_tools is NOT registered,
      and no "plan_related" group is created.
    """

    class TestReactAgent(react_agent_module.ReActAgent):
        def __init__(self):
            dummy_toolkit = DummyToolkit()
            super().__init__(
                name="test_agent",
                sys_prompt="test prompt",
                model=MagicMock(),
                formatter=MagicMock(),
                toolkit=dummy_toolkit,
                knowledge=None,
                enable_meta_tool=enable_meta_tool,
                plan_notebook=plan_notebook,
                enable_rewrite_query=False,
                parallel_tool_calls=False,
            )
            self.toolkit = dummy_toolkit

    agent = TestReactAgent()

    # Verify reset_equipped_tools registration
    reset_registered = any(
        func == agent.toolkit.reset_equipped_tools
        for func, _ in agent.toolkit.registered_functions
    )
    assert reset_registered == expect_reset_registered, (
        f"reset_equipped_tools registration expected={expect_reset_registered} but got {reset_registered}"
    )

    # Verify "plan_related" tool group creation
    plan_group_created = "plan_related" in agent.toolkit.created_tool_groups
    assert plan_group_created == expect_plan_group_created, (
        f"'plan_related' tool group creation expected={expect_plan_group_created} but got {plan_group_created}"
    )

    # If plan_notebook is provided and enable_meta_tool is False, tools must register without a group_name
    if plan_notebook and not enable_meta_tool:
        expected_tools = plan_notebook.list_tools()
        for tool in expected_tools:
            found = any(
                (func == tool and group is None)
                for func, group in agent.toolkit.registered_functions
            )
            assert found, (
                f"Expected tool {tool.name} to be registered without group_name when enable_meta_tool=False"
            )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))