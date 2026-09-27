import sys
import unittest
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from agentscope.tool import Bash


@unittest.skipIf(
    sys.platform == "win32",
    "Bash tool is not supported on Windows",
)
class BashCwdFail2PassTest(IsolatedAsyncioTestCase):
    """Fail2pass test for Bash tool cwd support."""

    async def test_cwd_argument_is_respected(self) -> None:
        """
        Test that the cwd argument to Bash constructor is passed to subprocess.

        Before the fix, the cwd argument is ignored and not passed to subprocess,
        so the test should fail (e.g., subprocess called without cwd).
        After the fix, the cwd argument is passed correctly and the test passes.
        """
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate = AsyncMock(return_value=(b"dummy output\n", b""))

        create_subprocess_mock = AsyncMock(return_value=process_mock)

        with patch(
            "agentscope.tool._builtin._bash.asyncio.create_subprocess_shell",
            create_subprocess_mock,
        ):
            chunks = []
            async for chunk in Bash(cwd="/tmp/testdir")(command="pwd"):
                chunks.append(chunk)

        # Assert that the subprocess was called with cwd="/tmp/testdir"
        self.assertIn(
            "cwd",
            create_subprocess_mock.call_args.kwargs,
            "cwd argument not passed to subprocess",
        )
        self.assertEqual(
            create_subprocess_mock.call_args.kwargs["cwd"],
            "/tmp/testdir",
            "cwd argument value mismatch",
        )

        # Assert that the tool yielded a running chunk with expected output type
        self.assertGreater(len(chunks), 0, "No chunks yielded by Bash tool")
        self.assertEqual(chunks[0].state, "running", "First chunk state is not 'running'")
        self.assertTrue(chunks[0].is_last, "First chunk is not marked as last")
