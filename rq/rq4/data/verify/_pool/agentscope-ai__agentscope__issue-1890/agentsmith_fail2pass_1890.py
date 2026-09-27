import asyncio
from contextlib import AsyncExitStack
from unittest import IsolatedAsyncioTestCase

import fakeredis.aioredis

from agentscope.app.message_bus import RedisMessageBus


def _make_bus(
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> RedisMessageBus:
    """Construct a :class:`RedisMessageBus` that uses *fake_redis*.

    The bus subclass overrides ``__aenter__`` so it talks to fakeredis
    instead of opening a real connection pool.

    Args:
        fake_redis (`fakeredis.aioredis.FakeRedis`):
            A fakeredis client whose pubsub / streams APIs are async.

    Returns:
        `RedisMessageBus`:
            A bus instance ready to be used as an async context manager.
    """

    class _FakeBus(RedisMessageBus):
        """Bus subclass that returns the supplied fakeredis client on
        context entry instead of building a real one."""

        async def __aenter__(self) -> "RedisMessageBus":
            self._client = fake_redis
            return self

        async def aclose(self) -> None:
            # The fakeredis client is owned by the test, not the bus.
            self._client = None

    return _FakeBus()


class TestInboxAndWakeupHelpers(IsolatedAsyncioTestCase):
    """Inbox + wakeup domain helpers used by team / tool-offload /
    scheduler to deliver work to idle sessions."""

    async def asyncSetUp(self) -> None:
        self.fr = fakeredis.aioredis.FakeRedis(decode_responses=True)
        self._stack = AsyncExitStack()
        self.bus = await self._stack.enter_async_context(_make_bus(self.fr))

    async def asyncTearDown(self) -> None:
        await self._stack.aclose()
        await self.fr.aclose()

    async def test_inbox_push_drain_round_trip(self) -> None:
        """``inbox_push`` payloads are returned by ``inbox_drain`` in
        push order, exactly once."""
        sid = "s-inbox"
        await self.bus.inbox_push(sid, {"hint": "a"})
        await self.bus.inbox_push(sid, {"hint": "b"})
        entries = await self.bus.inbox_drain(sid, max_count=10)
        self.assertEqual(
            [p["hint"] for _id, p in entries],
            ["a", "b"],
        )
        self.assertEqual(
            await self.bus.inbox_drain(sid, max_count=10),
            [],
        )

    async def test_enqueue_wakeup_signals_and_queues(self) -> None:
        """``enqueue_wakeup`` puts the payload on the durable queue and
        fires the signal channel; a subscriber and a ``dequeue_wakeups``
        call both see it."""
        ready = asyncio.Event()
        received: list[dict] = []

        async def _signal_consumer() -> None:
            async for payload in self.bus.subscribe_wakeup_signal(
                on_ready=ready.set,
            ):
                received.append(payload)
                break

        task = asyncio.create_task(_signal_consumer())
        await asyncio.wait_for(ready.wait(), timeout=2.0)

        await self.bus.enqueue_wakeup(
            user_id="u",
            session_id="s",
            agent_id="a",
        )
        await asyncio.wait_for(task, timeout=2.0)

        # Signal fired.
        self.assertEqual(len(received), 1)

        # Queue holds the structured entry. ``enqueue_wakeup`` is the
        # idle-wake shortcut, so the entry carries ``kind="wake"`` and a
        # null input alongside the routing fields.
        entries = await self.bus.dequeue_wakeups(max_count=10)
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0],
            {
                "user_id": "u",
                "session_id": "s",
                "agent_id": "a",
                "kind": "wake",
                "input": None,
            },
        )
