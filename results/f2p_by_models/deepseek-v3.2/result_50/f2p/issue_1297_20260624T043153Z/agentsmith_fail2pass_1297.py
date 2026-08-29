import asyncio
import pytest
from unittest.mock import patch, MagicMock
from agentscope.agent import AgentBase
from agentscope.message import Msg, TextBlock
from agentscope.hooks._studio_hooks import as_studio_forward_message_pre_print_hook


class MockAgent(AgentBase):  # Renamed from TestAgent to avoid pytest collection
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
    Test that the pre_print hook logs a warning and returns instead of raising
    when Studio is unreachable.
    """
    # Register hook with a non-existent Studio URL to force connection error
    MockAgent.register_class_hook(
        "pre_print",
        "studio_forward",
        lambda self, kwargs: as_studio_forward_message_pre_print_hook(
            self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
        ),
    )

    agent = MockAgent(name="MockAgent")
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    # Mock the correct logger path - agentscope uses 'as' logger
    with patch("agentscope.hooks._studio_hooks.logger") as mock_logger:
        # Mock requests.post to raise ConnectionError
        with patch("agentscope.hooks._studio_hooks.requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("Mock connection error")

            # Should not raise an exception
            asyncio.run(agent.reply(msg))

            # Verify warning was logged
            mock_logger.warning.assert_called_once()


def test_studio_pre_print_hook_retry_logic():
    """Test that the hook retries up to 3 times before degrading."""
    MockAgent.register_class_hook(
        "pre_print",
        "studio_forward",
        lambda self, kwargs: as_studio_forward_message_pre_print_hook(
            self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
        ),
    )

    agent = MockAgent(name="MockAgent")
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    with patch("agentscope.hooks._studio_hooks.logger") as mock_logger, \
         patch("agentscope.hooks._studio_hooks.requests.post") as mock_post:
        # Simulate repeated connection errors
        mock_post.side_effect = ConnectionError("Mock connection error")

        asyncio.run(agent.reply(msg))

        # Verify retries: 3 attempts + 1 initial = 4 calls total
        assert mock_post.call_count == 4
        # Verify warning logged after final failure
        mock_logger.warning.assert_called_once()


def test_studio_pre_print_hook_successful_forward():
    """Test that the hook works normally when Studio is reachable."""
    MockAgent.register_class_hook(
        "pre_print",
        "studio_forward",
        lambda self, kwargs: as_studio_forward_message_pre_print_hook(
            self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
        ),
    )

    agent = MockAgent(name="MockAgent")
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    with patch("agentscope.hooks._studio_hooks.logger") as mock_logger, \
         patch("agentscope.hooks._studio_hooks.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        asyncio.run(agent.reply(msg))

        # Verify request was made
        mock_post.assert_called_once()
        # No warning should be logged
        mock_logger.warning.assert_not_called()