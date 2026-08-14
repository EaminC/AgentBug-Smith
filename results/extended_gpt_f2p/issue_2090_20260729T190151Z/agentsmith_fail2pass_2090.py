import json
import asyncio

from unittest.async_case import IsolatedAsyncioTestCase

from agentscope.agent import Agent
from agentscope.state import AgentState
from agentscope.message import (
    UserMsg,
    AssistantMsg,
    ToolCallBlock,
    ToolResultBlock,
    ToolResultState,
    TextBlock,
)
from agentscope.tool import Toolkit
from tests.utils import MockModel
from utils import AnyString


class TestMultiToolContextCompression(IsolatedAsyncioTestCase):
    """Test that context compression does not split multi-tool call/result pairs."""

    async def test_multi_tool_call_result_batch_not_split(self) -> None:
        """Ensure that multi-tool call and result pairs are kept together after compression split."""

        agent = Agent(
            name="Friday",
            system_prompt="",
            model=MockModel(context_size=1_000),
            state=AgentState(
                session_id="multi-tool-compression",
                context=[
                    UserMsg("User", "old" * 80, id="old-user"),
                    AssistantMsg(
                        "Friday",
                        [
                            ToolCallBlock(
                                id="tc1",
                                name="first_tool",
                                input=json.dumps({"value": "a" * 80}),
                            ),
                            ToolCallBlock(
                                id="tc2",
                                name="second_tool",
                                input=json.dumps({"value": "b" * 80}),
                            ),
                            ToolResultBlock(
                                id="tc1",
                                name="first_tool",
                                output=[TextBlock(text="first result " * 8)],
                                state=ToolResultState.SUCCESS,
                            ),
                            ToolResultBlock(
                                id="tc2",
                                name="second_tool",
                                output=[TextBlock(text="second result " * 8)],
                                state=ToolResultState.SUCCESS,
                            ),
                            TextBlock(text="Both tools completed.", id="final-text"),
                        ],
                        id="multi-tool-msg",
                    ),
                    UserMsg("User", "latest question", id="latest-user"),
                ],
            ),
            toolkit=Toolkit(),
        )

        # Reserve tokens chosen to trigger splitting that would cause the bug
        to_compress, to_reserve = await agent._split_context_for_compression(
            to_reserved_tokens=86,
            tools=[],
        )

        # Assert that the to_compress contains the old user message and the full multi-tool assistant message,
        # including both tool calls and both results (no partial split)
        self.assertListEqual(
            [msg.model_dump() for msg in to_compress],
            [
                {
                    "id": "old-user",
                    "created_at": AnyString(),
                    "finished_at": AnyString(),
                    "name": "User",
                    "role": "user",
                    "content": [
                        {
                            "id": AnyString(),
                            "type": "text",
                            "text": "old" * 80,
                        },
                    ],
                    "metadata": {},
                    "usage": None,
                },
                {
                    "id": "multi-tool-msg",
                    "created_at": AnyString(),
                    "finished_at": None,
                    "name": "Friday",
                    "role": "assistant",
                    "content": [
                        {
                            "id": "tc1",
                            "type": "tool_call",
                            "name": "first_tool",
                            "input": json.dumps({"value": "a" * 80}),
                            "state": "pending",
                            "suggested_rules": [],
                        },
                        {
                            "id": "tc2",
                            "type": "tool_call",
                            "name": "second_tool",
                            "input": json.dumps({"value": "b" * 80}),
                            "state": "pending",
                            "suggested_rules": [],
                        },
                        {
                            "id": "tc1",
                            "type": "tool_result",
                            "name": "first_tool",
                            "output": [
                                {
                                    "id": AnyString(),
                                    "type": "text",
                                    "text": "first result " * 8,
                                },
                            ],
                            "state": "success",
                            "metadata": {},
                        },
                        {
                            "id": "tc2",
                            "type": "tool_result",
                            "name": "second_tool",
                            "output": [
                                {
                                    "id": AnyString(),
                                    "type": "text",
                                    "text": "second result " * 8,
                                },
                            ],
                            "state": "success",
                            "metadata": {},
                        },
                    ],
                    "metadata": {},
                    "usage": None,
                },
            ],
        )

        # Assert that the reserved context contains the final text block and the latest user message
        self.assertListEqual(
            [msg.model_dump() for msg in to_reserve],
            [
                {
                    "id": "multi-tool-msg",
                    "created_at": AnyString(),
                    "finished_at": None,
                    "name": "Friday",
                    "role": "assistant",
                    "content": [
                        {
                            "id": "final-text",
                            "type": "text",
                            "text": "Both tools completed.",
                        },
                    ],
                    "metadata": {},
                    "usage": None,
                },
                {
                    "id": "latest-user",
                    "created_at": AnyString(),
                    "finished_at": AnyString(),
                    "name": "User",
                    "role": "user",
                    "content": [
                        {
                            "id": AnyString(),
                            "type": "text",
                            "text": "latest question",
                        },
                    ],
                    "metadata": {},
                    "usage": None,
                },
            ],
        )
