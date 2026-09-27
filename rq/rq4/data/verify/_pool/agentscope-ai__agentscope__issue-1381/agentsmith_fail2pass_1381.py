# -*- coding: utf-8 -*-
"""Unit tests for AsyncSQLAlchemyMemory concurrent writes (Issue #1381)."""
import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import MagicMock
from unittest.async_case import IsolatedAsyncioTestCase

# 1. Force workspace source priority
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 2. Mock mcp package and submodules to prevent top-level import conflicts
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

# 3. Import dependencies
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select as sa_select

from agentscope.memory import AsyncSQLAlchemyMemory
from agentscope.message import Msg


class TestAsyncSQLAlchemyMemoryConcurrency(IsolatedAsyncioTestCase):
    """
    Issue #1381 / PR #1390:
    When parallel_tool_calls=True, concurrent calls to memory.add() without
    lock synchronization cause duplicate primary keys and race conditions in _get_next_index().
    """

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
        )
        self.memory = AsyncSQLAlchemyMemory(
            session_id="session_concurrent_test",
            user_id="user_concurrent_test",
            engine_or_session=self.engine,
        )

    async def test_concurrent_add(self) -> None:
        """Test that concurrent add() calls don't cause IntegrityError or duplicate indices."""
        messages = [
            Msg("system", f"Tool result {i}", "system") for i in range(20)
        ]

        # Add all messages concurrently (simulating parallel tool execution)
        await asyncio.gather(
            *(self.memory.add(msg) for msg in messages),
        )

        # Verify all messages were successfully persisted
        stored = await self.memory.get_memory()
        self.assertEqual(len(stored), len(messages))

        # Verify indices are unique and contiguous
        result = await self.memory.session.execute(
            sa_select(self.memory.MessageTable.index)
            .filter(
                self.memory.MessageTable.session_id == self.memory.session_id,
            )
            .order_by(self.memory.MessageTable.index),
        )
        indices = [row[0] for row in result.fetchall()]
        self.assertEqual(
            len(set(indices)),
            len(messages),
            "Indices must be unique across concurrent writes",
        )
        self.assertEqual(
            indices,
            list(range(len(messages))),
            "Indices must be contiguous without gaps or overlaps",
        )

    async def asyncTearDown(self) -> None:
        await self.memory.clear()
        if hasattr(self.memory, "close"):
            await self.memory.close()
        await self.engine.dispose()