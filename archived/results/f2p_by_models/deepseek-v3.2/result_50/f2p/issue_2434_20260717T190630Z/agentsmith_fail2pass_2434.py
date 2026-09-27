import asyncio

from crewai.tools import BaseTool


class AsyncTool(BaseTool):
    """Test implementation with an asynchronous _run method"""
    name: str = "async_tool"
    description: str = "An asynchronous tool for testing"

    async def _run(self, input_text: str) -> str:
        """Process input text asynchronously."""
        await asyncio.sleep(0.1)  # Simulate async operation
        return f"Processed {input_text} asynchronously"


def test_async_tool_run_returns_awaited_result():
    """Test that BaseTool.run correctly awaits an async _run and returns the result."""
    tool = AsyncTool()
    result = tool.run(input_text="hello")
    # On buggy code, result is a coroutine, so this assertion fails
    assert not asyncio.iscoroutine(result)
    assert result == "Processed hello asynchronously"


def test_sync_tool_run_returns_direct_result():
    """Test that sync _run continues to work correctly."""

    class SyncTool(BaseTool):
        name: str = "sync_tool"
        description: str = "A synchronous tool for testing"

        def _run(self, input_text: str) -> str:
            return f"Processed {input_text} synchronously"

    tool = SyncTool()
    result = tool.run(input_text="test")
    assert not asyncio.iscoroutine(result)
    assert result == "Processed test synchronously"
