from unittest.async_case import IsolatedAsyncioTestCase

from agentscope.message import ThinkingBlock, TextBlock, UserMsg
from agentscope.model import ChatResponse
from agentscope.agent import Agent
from agentscope.tool import Toolkit
from agentscope.model import FinishedReason


class ThinkingOnlyResponseTest(IsolatedAsyncioTestCase):
    """Test that ReActAgent does not exit loop prematurely on thinking-only responses."""

    async def asyncSetUp(self) -> None:
        """Set up an agent with a mock model that can simulate thinking-only responses."""
        # Use the built-in MockModel from utils if available, else fallback to Agent's model
        # We want to simulate multiple LLM responses: first thinking-only, then text.
        from tests.utils import MockModel

        self.model = MockModel()
        self.agent = Agent(
            name="TestAgent",
            system_prompt="You are a helpful assistant.",
            model=self.model,
            toolkit=Toolkit(),
        )

    async def test_thinking_only_response_does_not_exit_loop(self) -> None:
        """The agent should continue reasoning if the LLM returns only thinking blocks."""

        # Setup the mock model to return two responses:
        # 1) A thinking-only block (should not end the loop)
        # 2) A normal text block (final answer)
        self.model.set_responses(
            [
                [
                    ChatResponse(
                        content=[ThinkingBlock(thinking="Processing...")],
                        is_last=True,
                        finished_reason=FinishedReason.COMPLETED,
                    ),
                ],
                [
                    ChatResponse(
                        content=[TextBlock(text="Here is the final answer.")],
                        is_last=True,
                        finished_reason=FinishedReason.COMPLETED,
                    ),
                ],
            ]
        )

        # Send a user message to trigger the agent's reasoning loop
        user_msg = UserMsg(name="user", content="Please think and answer.")

        # Call the agent's reply method which triggers the reasoning loop
        reply_msg = await self.agent.reply(user_msg)

        # The model's internal call counter should be 2, meaning it did not exit after the thinking-only response
        self.assertEqual(self.model.cnt, 2)

        # The final reply message should contain the visible text, not just thinking
        content_texts = [block.text for block in reply_msg.content if hasattr(block, "text")]
        self.assertIn("Here is the final answer.", content_texts)

        # The reply message should not be empty or contain only thinking blocks
        has_thinking_only = all(
            isinstance(block, ThinkingBlock) for block in reply_msg.content
        )
        self.assertFalse(has_thinking_only)

        # The context should contain both the thinking block and the final answer in the same assistant message
        # Check the last assistant message in context
        last_assistant_msg = None
        for msg in reversed(self.agent.state.context):
            if msg.name == self.agent.name and msg.role == "assistant":
                last_assistant_msg = msg
                break
        self.assertIsNotNone(last_assistant_msg)

        # It should contain both thinking and text blocks
        types_in_content = {block.type for block in last_assistant_msg.content}
        self.assertIn("thinking", types_in_content)
        self.assertIn("text", types_in_content)

    async def asyncTearDown(self) -> None:
        """Clean up after tests."""
        pass
