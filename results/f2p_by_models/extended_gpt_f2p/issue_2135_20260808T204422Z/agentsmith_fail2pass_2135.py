import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from agentscope.message import ThinkingBlock, TextBlock
from agentscope.model import AnthropicChatModel
from agentscope.credential import AnthropicCredential


class TestAnthropicExtendedThinkingFail2Pass(unittest.IsolatedAsyncioTestCase):
    """Fail2pass test for Anthropic extended thinking redacted_thinking block preservation.

    This test simulates a multi-turn conversation where the first response contains
    a redacted_thinking block and the second call reuses the history.

    Before the fix, the second call raises InternalServerError 500 due to
    modification of the redacted_thinking block.

    After the fix, the call succeeds and returns a valid response.
    """

    async def asyncSetUp(self) -> None:
        self.model = AnthropicChatModel(
            credential=AnthropicCredential(api_key="test"),
            model="claude-2",
            stream=False,
        )

    @patch("anthropic.AsyncAnthropic")
    async def test_redacted_thinking_block_preserved_across_calls(
        self,
        mock_client_cls: MagicMock,
    ) -> None:
        # Prepare the first mocked response with a redacted_thinking block
        redacted_block = MagicMock()
        redacted_block.type = "redacted_thinking"
        redacted_block.data = "encrypted_payload_123"

        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.thinking = "visible thought"
        thinking_block.signature = "sig_visible"

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello from assistant."

        first_response = MagicMock()
        first_response.id = "msg-1"
        first_response.content = [thinking_block, redacted_block, text_block]
        first_response.usage = MagicMock()
        first_response.usage.input_tokens = 10
        first_response.usage.output_tokens = 15
        first_response.usage.cache_creation_input_tokens = 0
        first_response.usage.cache_read_input_tokens = 0

        # The second mocked response to simulate a successful follow-up call
        second_response = MagicMock()
        second_response.id = "msg-2"
        second_response.content = [text_block]
        second_response.usage = MagicMock()
        second_response.usage.input_tokens = 20
        second_response.usage.output_tokens = 10
        second_response.usage.cache_creation_input_tokens = 0
        second_response.usage.cache_read_input_tokens = 0

        # Mock the messages.create method to return first_response on first call,
        # and second_response on second call.
        mock_create = AsyncMock(side_effect=[first_response, second_response])
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        mock_client_cls.return_value = mock_client

        # First call: no history, get initial response with redacted_thinking block
        result1 = await self.model([])

        # Validate first call returns ThinkingBlock with redacted_thinking_data and text
        self.assertTrue(any(
            isinstance(b, ThinkingBlock) and getattr(b, "redacted_thinking_data", None) == "encrypted_payload_123"
            for b in result1.content
        ))
        self.assertTrue(any(
            isinstance(b, ThinkingBlock) and b.thinking == "visible thought" and b.signature == "sig_visible"
            for b in result1.content
        ))
        self.assertTrue(any(
            isinstance(b, TextBlock) and b.text == "Hello from assistant."
            for b in result1.content
        ))

        # Prepare the history for the second call: simulate passing back the full assistant message
        # including the redacted_thinking block exactly as received.
        # We construct message history as a list of messages with content blocks from result1.
        # The AnthropicChatModel expects a list of messages (UserMsg, AssistantMsg, etc.),
        # so we must wrap the content blocks into an AssistantMsg to pass as history.

        from agentscope.message import AssistantMsg

        # Wrap the content blocks into an AssistantMsg to simulate prior assistant message
        prior_assistant_msg = AssistantMsg(name="assistant", content=result1.content)

        # The model call will internally reformat and send messages.create with the history.
        # Call the model again with the previous assistant message as history
        # to simulate multi-turn conversation replay.

        result2 = await self.model([prior_assistant_msg])

        # The second call should succeed without InternalServerError 500.
        # Validate the response content matches the mocked second_response content.
        self.assertTrue(any(
            isinstance(b, TextBlock) and b.text == "Hello from assistant."
            for b in result2.content
        ))
        self.assertEqual(result2.id, "msg-2")

        # Also verify that the mock was called twice
        self.assertEqual(mock_create.call_count, 2)

        # Verify that the redacted_thinking block was passed back exactly unmodified in the second call
        # by inspecting the arguments of the second call to messages.create
        second_call_args, second_call_kwargs = mock_create.call_args_list[1]

        # The messages argument is expected in kwargs as 'messages'
        messages_sent = second_call_kwargs.get("messages", None)
        self.assertIsNotNone(messages_sent)

        # Find the last assistant message in messages_sent
        last_assistant = None
        for msg in reversed(messages_sent):
            if msg.get("role") == "assistant":
                last_assistant = msg
                break
        self.assertIsNotNone(last_assistant)

        # Check that the redacted_thinking block is present exactly as in first response
        found_redacted = False
        for block in last_assistant.get("content", []):
            if block.get("type") == "redacted_thinking" and block.get("data") == "encrypted_payload_123":
                found_redacted = True
                break
        self.assertTrue(found_redacted)


if __name__ == "__main__":
    unittest.main()
