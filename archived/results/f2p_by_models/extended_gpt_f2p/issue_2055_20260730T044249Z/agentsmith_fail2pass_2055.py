import tempfile
import asyncio
from unittest.async_case import IsolatedAsyncioTestCase

from agentscope.workspace import LocalWorkspace
from agentscope.tool import Bash, Edit, Glob, Grep, LocalBackend, Read, Write


class TestLocalWorkspaceListToolsFail2Pass(IsolatedAsyncioTestCase):
    """Regression test for LocalWorkspace.list_tools AttributeError.

    This test triggers the bug where LocalWorkspace.list_tools() raises
    AttributeError due to missing _glob_helper_path attribute. The test
    will fail on the buggy codebase and pass after the fix is applied.
    """

    async def test_list_tools_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            workspace = LocalWorkspace(workdir=workdir)
            await workspace.initialize()
            try:
                tools = await workspace.list_tools()
            finally:
                await workspace.close()

        # Assert that the returned tools list contains the expected builtin tools
        self.assertEqual(len(tools), 6)
        self.assertSetEqual(
            {type(tool) for tool in tools},
            {Bash, Edit, Glob, Grep, Read, Write},
        )
        # Assert each tool uses LocalBackend as backend
        for tool in tools:
            self.assertIsInstance(tool._backend, LocalBackend)
