import os
import json
import tempfile
from unittest.async_case import IsolatedAsyncioTestCase

import aiofiles

from agentscope.mcp import MCPClient, StdioMCPConfig
from agentscope.workspace import LocalWorkspace


class TestLocalWorkspaceMCPInit(IsolatedAsyncioTestCase):
    """Test MCP loading error handling in LocalWorkspace.initialize().

    Covers:
    - Invalid entries in persisted .mcp are skipped (not crashing)
    - Stateful MCP connection failures are skipped (not crashing)
    - Valid MCPs still load despite invalid neighbours
    """

    async def asyncSetUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()

    async def asyncTearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    async def _write_mcp_file(self, entries: list[dict]) -> str:
        """Write a list of MCP config dicts to ``<workdir>/.mcp``.

        Args:
            entries: List of raw MCP config dicts.

        Returns:
            The path to the written file.
        """
        mcp_file = os.path.join(self.temp_dir.name, ".mcp")
        async with aiofiles.open(mcp_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(entries, indent=2, ensure_ascii=False))
        return mcp_file

    @staticmethod
    def _make_http_mcp(name: str) -> dict:
        """Return a valid stateless HTTP MCP entry."""
        return {
            "name": name,
            "is_stateful": False,
            "mcp_config": {
                "type": "http_mcp",
                "url": "http://localhost:19999/nonexistent",
            },
            "enable_tools": None,
            "disable_tools": None,
            "execution_timeout": None,
        }

    @staticmethod
    def _make_bad_stdio_mcp(name: str) -> dict:
        """Return an invalid STDIO MCP entry (is_stateful=False)."""
        return {
            "name": name,
            "is_stateful": False,
            "mcp_config": {
                "type": "stdio_mcp",
                "command": "nonexistent_cmd",
            },
            "enable_tools": None,
            "disable_tools": None,
            "execution_timeout": None,
        }

    # -----------------------------------------------------------------
    #  persisted .mcp
    # -----------------------------------------------------------------

    async def test_initialize_skips_bad_entry_keeps_good(self) -> None:
        """A persisted .mcp with one bad entry should skip it and still
        load the valid entry."""
        await self._write_mcp_file(
            [
                self._make_bad_stdio_mcp("bad_one"),
                self._make_http_mcp("good_one"),
            ],
        )

        ws = LocalWorkspace(workdir=self.temp_dir.name)
        await ws.initialize()

        mcps = await ws.list_mcps()
        names = [m.name for m in mcps]
        self.assertIn("good_one", names)
        self.assertNotIn("bad_one", names)

    # -----------------------------------------------------------------
    #  default_mcps + connect failure
    # -----------------------------------------------------------------

    async def test_initialize_connect_failure_removes_mcp(self) -> None:
        """A stateful MCP whose connect() raises should not crash
        initialize() and should be removed from the MCP list."""
        ws = LocalWorkspace(
            workdir=self.temp_dir.name,
            default_mcps=[
                MCPClient(
                    name="will_fail_connect",
                    is_stateful=True,
                    mcp_config=StdioMCPConfig(
                        command="nonexistent_command_xyz",
                    ),
                ),
            ],
        )
        await ws.initialize()
        self.assertTrue(ws.is_alive)
        names = [m.name for m in await ws.list_mcps()]
        self.assertNotIn("will_fail_connect", names)
