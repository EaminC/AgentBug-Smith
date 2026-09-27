import json
import os
import tempfile
import unittest

from agentscope.model import StructuredResponse
from agentscope.agent import Agent, ContextConfig
from agentscope.state import AgentState
from agentscope.message import UserMsg, AssistantMsg, ToolCallBlock
from agentscope.tool import Toolkit
from tests.utils import MockModel


class TestReadCacheEvictionOnCompression(unittest.IsolatedAsyncioTestCase):
    async def test_context_compression_clears_evicted_read_cache(self) -> None:
        """Read cache is cleared when its Read block is compressed out."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("content\n")

            model = MockModel(context_size=100)
            agent = Agent(
                name="Friday",
                system_prompt="".join(["0" for _ in range(20 * 4)]),
                model=model,
                context_config=ContextConfig(
                    trigger_ratio=0.7,
                    reserve_ratio=0.4,
                ),
                state=AgentState(
                    session_id="123",
                    context=[
                        AssistantMsg(
                            "Friday",
                            [
                                ToolCallBlock(
                                    id="read-call-1",
                                    name="Read",
                                    input=json.dumps(
                                        {"file_path": file_path},
                                    ),
                                ),
                            ],
                            id="1",
                        ),
                        UserMsg(
                            "User",
                            "".join(["2" for _ in range(30 * 4)]),
                            id="2",
                        ),
                        UserMsg(
                            "User",
                            "".join(["3" for _ in range(10 * 4)]),
                            id="3",
                        ),
                    ],
                ),
                toolkit=Toolkit(),
            )
            await agent.state.tool_context.cache_file(
                file_path=file_path,
                lines=["content\n"],
            )
            self.assertIsNotNone(
                await agent.state.tool_context.get_cache(file_path),
            )

            model.set_structured_response(
                StructuredResponse(
                    content={
                        "task_overview": "1",
                        "current_state": "2",
                        "important_discoveries": "3",
                        "next_steps": "4",
                        "context_to_preserve": "5",
                    },
                ),
            )

            await agent.compress_context()

            self.assertIsNone(
                await agent.state.tool_context.get_cache(file_path),
            )

    async def test_context_compression_keeps_reserved_read_cache(self) -> None:
        """Read cache is kept when the same file is still read in context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("content\n")

            model = MockModel(context_size=100)
            agent = Agent(
                name="Friday",
                system_prompt="".join(["0" for _ in range(20 * 4)]),
                model=model,
                context_config=ContextConfig(
                    trigger_ratio=0.7,
                    reserve_ratio=0.6,
                ),
                state=AgentState(
                    session_id="123",
                    context=[
                        AssistantMsg(
                            "Friday",
                            [
                                ToolCallBlock(
                                    id="read-call-1",
                                    name="Read",
                                    input=json.dumps(
                                        {"file_path": file_path},
                                    ),
                                ),
                            ],
                            id="1",
                        ),
                        UserMsg(
                            "User",
                            "".join(["2" for _ in range(30 * 4)]),
                            id="2",
                        ),
                        AssistantMsg(
                            "Friday",
                            [
                                ToolCallBlock(
                                    id="read-call-2",
                                    name="Read",
                                    input=json.dumps(
                                        {"file_path": file_path},
                                    ),
                                ),
                            ],
                            id="3",
                        ),
                    ],
                ),
                toolkit=Toolkit(),
            )
            await agent.state.tool_context.cache_file(
                file_path=file_path,
                lines=["content\n"],
            )

            model.set_structured_response(
                StructuredResponse(
                    content={
                        "task_overview": "1",
                        "current_state": "2",
                        "important_discoveries": "3",
                        "next_steps": "4",
                        "context_to_preserve": "5",
                    },
                ),
            )

            await agent.compress_context()

            self.assertIsNotNone(
                await agent.state.tool_context.get_cache(file_path),
            )

    async def test_context_compression_clears_unreferenced_read_cache(self) -> None:
        """Read cache is cleared when no reserved Read references it."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("content\n")

            model = MockModel(context_size=100)
            agent = Agent(
                name="Friday",
                system_prompt="".join(["0" for _ in range(20 * 4)]),
                model=model,
                context_config=ContextConfig(
                    trigger_ratio=0.7,
                    reserve_ratio=0.4,
                ),
                state=AgentState(
                    session_id="123",
                    context=[
                        UserMsg(
                            "User",
                            "".join(["2" for _ in range(60 * 4)]),
                            id="1",
                        ),
                        UserMsg(
                            "User",
                            "".join(["3" for _ in range(30 * 4)]),
                            id="2",
                        ),
                    ],
                ),
                toolkit=Toolkit(),
            )
            await agent.state.tool_context.cache_file(
                file_path=file_path,
                lines=["content\n"],
            )

            model.set_structured_response(
                StructuredResponse(
                    content={
                        "task_overview": "1",
                        "current_state": "2",
                        "important_discoveries": "3",
                        "next_steps": "4",
                        "context_to_preserve": "5",
                    },
                ),
            )

            await agent.compress_context()

            self.assertIsNone(
                await agent.state.tool_context.get_cache(file_path),
            )
