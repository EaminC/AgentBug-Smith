import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from agentscope.tool import PowerShell, Bash, Edit, Glob, Grep, Read, Write
from agentscope.workspace import LocalWorkspace, WorkspaceBase


class TestLocalWorkspaceToolsWindowsFail2Pass(IsolatedAsyncioTestCase):
    """Test that LocalWorkspace.list_tools returns PowerShell on Windows and Bash on POSIX."""

    async def test_list_tools_builtin_posix_uses_bash(self) -> None:
        """A POSIX local workspace returns Bash and filesystem tools."""
        with tempfile.TemporaryDirectory() as workdir:
            workspace = LocalWorkspace(workdir=workdir)
            await workspace.initialize()
            try:
                with patch(
                    "agentscope.workspace._local_workspace.os",
                    SimpleNamespace(name="posix"),
                ):
                    tools = await workspace.list_tools()
            finally:
                await workspace.close()

        self.assertEqual(len(tools), 6)
        self.assertSetEqual(
            {type(tool) for tool in tools},
            {Bash, Edit, Glob, Grep, Read, Write},
        )
        for tool in tools:
            self.assertIsInstance(tool._backend, type(workspace.get_backend()))

    async def test_list_tools_builtin_windows_uses_powershell(self) -> None:
        """A Windows local workspace returns PowerShell, not Bash."""
        with tempfile.TemporaryDirectory() as workdir:
            workspace = LocalWorkspace(workdir=workdir)
            await workspace.initialize()
            try:
                with patch(
                    "agentscope.workspace._local_workspace.os",
                    SimpleNamespace(name="nt"),
                ):
                    tools = await workspace.list_tools()
            finally:
                await workspace.close()

        self.assertEqual(len(tools), 6)
        self.assertSetEqual(
            {type(tool) for tool in tools},
            {PowerShell, Edit, Glob, Grep, Read, Write},
        )
        for tool in tools:
            self.assertIsInstance(tool._backend, type(workspace.get_backend()))

    async def test_windows_shell_switch_is_local_workspace_behavior(self) -> None:
        """Ensure LocalWorkspace.list_tools does not delegate to WorkspaceBase on Windows."""
        workspace = LocalWorkspace(workdir="workspace")
        backend = workspace.get_backend()

        with (
            patch.object(
                WorkspaceBase,
                "list_tools",
                new=AsyncMock(side_effect=AssertionError("must not delegate")),
            ),
            patch(
                "agentscope.workspace._local_workspace.os",
                SimpleNamespace(name="nt"),
            ),
        ):
            tools = await workspace.list_tools()

        self.assertIsInstance(tools[0], PowerShell)
        self.assertIs(tools[0]._backend, backend)


if __name__ == "__main__":
    unittest.main()
