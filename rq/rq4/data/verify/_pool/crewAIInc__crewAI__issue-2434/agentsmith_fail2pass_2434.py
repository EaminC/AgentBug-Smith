import sys
from pathlib import Path

# 1. Force workspace source priority
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import asyncio
from crewai.tools import BaseTool


class AsyncTool(BaseTool):
    """Test implementation with an asynchronous _run method"""
    name: str = "async_tool"
    description: str = "An asynchronous tool for testing"

    async def _run(self, input_text: str) -> str:
        """Process input text asynchronously."""
        await asyncio.sleep(0.01)
        return f"Processed {input_text} asynchronously"


class SyncTool(BaseTool):
    """Test implementation with a synchronous _run method"""
    name: str = "sync_tool"
    description: str = "A synchronous tool for testing"

    def _run(self, input_text: str) -> str:
        return f"Processed {input_text} synchronously"


def test_async_tool_run_returns_awaited_result():
    """
    Issue #2434 / PR #2570:
    When _run returns a coroutine (async tool), BaseTool.run must execute and await
    the coroutine rather than returning the raw coroutine object.
    """
    tool = AsyncTool()
    result = tool.run(input_text="hello")

    # Before fix: result is <coroutine object AsyncTool._run> -> FAILS (rc1=1)
    # After fix: result is "Processed hello asynchronously" -> PASSES (rc2=0)
    assert not asyncio.iscoroutine(result)
    assert result == "Processed hello asynchronously"


def test_sync_tool_run_returns_direct_result():
    """Verify synchronous tools continue to run and return directly."""
    tool = SyncTool()
    result = tool.run(input_text="test")

    assert not asyncio.iscoroutine(result)
    assert result == "Processed test synchronously"