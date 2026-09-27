import sys
from pathlib import Path

# 1. Force Python to import from /app/src instead of static site-packages
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from unittest.mock import MagicMock, patch
import asyncio
import pytest

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

# 3. Import AgentScope components from live /app/src
from agentscope.agent import AgentBase
from agentscope.message import Msg, TextBlock
from agentscope.hooks._studio_hooks import as_studio_forward_message_pre_print_hook


class MockAgent(AgentBase):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._disable_console_output = False

    async def reply(self, msg: Msg) -> Msg:
        await self.print(msg)
        return msg

    async def observe(self, msg: Msg) -> None:
        pass

    async def handle_interrupt(self, *args, **kwargs) -> Msg:
        return Msg("test", "Interrupt handled", "assistant")


def test_studio_pre_print_hook_graceful_degradation_on_connection_error():
    """
    Issue #1297 / PR #1298:
    When Studio is disconnected or unreachable, as_studio_forward_message_pre_print_hook
    must not crash the Agent by raising ConnectionError after retries.
    """
    MockAgent.register_class_hook(
        "pre_print",
        "studio_forward",
        lambda self, kwargs: as_studio_forward_message_pre_print_hook(
            self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
        ),
    )

    agent = MockAgent(name="MockAgent")
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    with patch("agentscope.hooks._studio_hooks.requests.post") as mock_post:
        # Simulate unreachable Studio service
        mock_post.side_effect = ConnectionError("Connection refused by Studio")

        # Before PR #1298: raises ConnectionError -> FAILS (rc1=1)
        # After PR #1298: catches error, logs warning, returns -> PASSES (rc2=0)
        result = asyncio.run(agent.reply(msg))
        assert result is not None
        assert mock_post.call_count == 4  # 1 initial + 3 retries


def test_studio_pre_print_hook_successful_forward():
    """Verify normal behavior when Studio is reachable."""
    MockAgent.register_class_hook(
        "pre_print",
        "studio_forward",
        lambda self, kwargs: as_studio_forward_message_pre_print_hook(
            self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
        ),
    )

    agent = MockAgent(name="MockAgent")
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    with patch("agentscope.hooks._studio_hooks.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        result = asyncio.run(agent.reply(msg))
        assert result is not None
        mock_post.assert_called_once()