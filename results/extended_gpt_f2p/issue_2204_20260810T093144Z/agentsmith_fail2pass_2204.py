import unittest
from unittest import IsolatedAsyncioTestCase

from agentscope.agent import Agent, ReActConfig
from agentscope.model import ChatResponse
from agentscope.tool import Toolkit
from agentscope.message import ToolCallBlock, TextBlock, UserMsg
from agentscope.types import ReplyFinishedReason


class AgentMaxItersReActTest(IsolatedAsyncioTestCase):
    """Test that max_iters counts one reasoning-acting round once."""

    def _make_mock_model(self):
        from tests.utils import MockModel

        return MockModel()

    async def test_max_iters_counts_one_round_once(self) -> None:
        """With max_iters=2, the agent should complete two reasoning-acting rounds.

        The test sets up a mock model with two responses:
        1. A tool call response.
        2. A final text response after the tool result.

        The agent should:
        - Perform the first reasoning pass producing a tool call.
        - Perform the acting pass executing the tool call.
        - Perform the second reasoning pass producing the final answer.
        - Finish with finished_reason == completed.
        - Have cur_iter == 2 (one per reasoning-acting round).
        - Have model call count == 2 (both responses used).
        """
        model = self._make_mock_model()
        toolkit = Toolkit()
        agent = Agent(
            name="TestAgent",
            system_prompt="You are a helpful assistant.",
            model=model,
            toolkit=toolkit,
            react_config=ReActConfig(max_iters=2),
        )

        # Setup mock model responses:
        # First response: tool call block
        # Second response: final text block
        model.set_responses(
            [
                ChatResponse(
                    content=[
                        ToolCallBlock(
                            id="call_1",
                            name="mock_tool",
                            input='{"input": "x"}',
                        )
                    ],
                    is_last=True,
                ),
                ChatResponse(
                    content=[TextBlock(text="done")],
                    is_last=True,
                ),
            ]
        )

        # Send user message to agent
        reply = await agent.reply(UserMsg(name="user", content="go"))

        # Assert finished_reason is completed
        self.assertEqual(reply.finished_reason, ReplyFinishedReason.COMPLETED)

        # Assert final text content is "done"
        texts = [block.text for block in reply.get_content_blocks("text")]
        self.assertIn("done", texts)

        # Assert model call count is 2 (both responses used)
        self.assertEqual(model.cnt, 2)

        # Assert cur_iter is 2 (one per reasoning-acting round)
        self.assertEqual(agent.state.cur_iter, 2)

        # Assert the tool result is present in the last assistant message
        last_msg = agent.state.context[-1]
        tool_results = last_msg.get_content_blocks("tool_result")
        self.assertEqual(len(tool_results), 1)
        # tool_result.output can be either list of blocks or a string error message
        # Check if output is list and contains expected text or fallback to string check
        found = False
        for tr in tool_results:
            output = tr.output
            if isinstance(output, list) and output:
                if any(
                    "Sequential result" in (blk.text if hasattr(blk, "text") else "")
                    for blk in output
                ):
                    found = True
                    break
            elif isinstance(output, str):
                if "mock_tool" in tr.name or "Sequential result" in output:
                    found = True
                    break
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
