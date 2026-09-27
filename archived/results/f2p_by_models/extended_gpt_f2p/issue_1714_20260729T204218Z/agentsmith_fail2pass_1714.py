import sys
import asyncio
import unittest
from unittest.async_case import IsolatedAsyncioTestCase

from agentscope.tool import Bash
from agentscope.tool._builtin._bash import _subprocess_creation_kwargs


class TestExecuteShellCommandWindowBehavior(IsolatedAsyncioTestCase):
    """
    Test that executing shell commands via Bash tool does not pop up a console window on Windows.

    This test indirectly verifies that the subprocess is created with the CREATE_NO_WINDOW flag on Windows,
    which prevents the console window from appearing and stealing focus.

    The test runs a simple echo command and checks the output.
    """

    async def asyncSetUp(self) -> None:
        self.bash_tool = Bash()

    async def test_command_executes_without_console_window(self) -> None:
        # Run a simple command that produces output
        chunks = []
        async for chunk in self.bash_tool(command="echo HelloWindowTest"):
            chunks.append(chunk)

        # There should be exactly one chunk with running state and is_last True
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertEqual(chunk.state, "running")
        self.assertTrue(chunk.is_last)

        # The output should contain the echoed text
        texts = [block.text for block in chunk.content if hasattr(block, "text")]
        output_text = "".join(texts)
        self.assertIn("HelloWindowTest", output_text)

    async def test_subprocess_creation_flags_on_windows(self) -> None:
        # This test checks that on Windows, the subprocess creation flags include CREATE_NO_WINDOW
        # and on non-Windows, no extra flags are set.

        # We test the helper function _subprocess_creation_kwargs directly
        if sys.platform == "win32":
            kwargs = _subprocess_creation_kwargs()
            self.assertIn("creationflags", kwargs)
            self.assertEqual(kwargs["creationflags"], 0x08000000)
        else:
            kwargs = _subprocess_creation_kwargs()
            self.assertEqual(kwargs, {})


if __name__ == "__main__":
    unittest.main()
