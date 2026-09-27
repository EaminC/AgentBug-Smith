import asyncio
from typing import Any
from pydantic import BaseModel
import pytest

from agentscope.agent import Agent
from agentscope.app._manager import ChatRunRegistry
from agentscope.event import ReplyEndEvent
from agentscope.message import UserMsg
from agentscope.model import ChatResponse
from agentscope.tool import Toolkit
from tests.utils import MockModel


@pytest.mark.asyncio
class TestChatModelBaseInterruption:
    async def _assert_chat_model_base_interruption(
        self,
        structured_schema: type[BaseModel] | None = None,
    ) -> None:
        """A cancelled model call must terminate the reply as interrupted."""

        class InterruptibleModel(MockModel):
            """ChatModelBase implementation that blocks on its first call."""

            def __init__(self) -> None:
                super().__init__(stream=False)
                self.call_started = asyncio.Event()
                self.call_count = 0

            async def _call_api(
                self,
                *_args: Any,
                **_kwargs: Any,
            ) -> ChatResponse:
                self.call_count += 1
                if self.call_count > 1:
                    raise AssertionError(
                        "Interrupted reply made another model call",
                    )
                self.call_started.set()
                await asyncio.Event().wait()
                raise AssertionError("Unreachable")

        model = InterruptibleModel()
        agent = Agent(
            name="InterruptibleAgent",
            system_prompt="You are a test agent.",
            model=model,
            toolkit=Toolkit(),
        )
        registry = ChatRunRegistry()
        end_events: list[ReplyEndEvent] = []

        async def _chat_run() -> None:
            async for event in agent.reply_stream(
                UserMsg(name="user", content="Hello"),
                structured_schema=structured_schema,
            ):
                if isinstance(event, ReplyEndEvent):
                    end_events.append(event)

        task = registry.spawn(
            _chat_run(),
            session_id="chat-model-base-interruption",
        )
        await asyncio.wait_for(model.call_started.wait(), timeout=1)
        task.cancel()
        await asyncio.wait_for(task, timeout=1)

        assert model.call_count == 1
        assert len(end_events) == 1
        assert end_events[0].finished_reason == "interrupted"

    async def test_chat_model_base_interruption(self) -> None:
        """ChatModelBase cancellation is reported as interrupted."""
        await self._assert_chat_model_base_interruption()

    async def test_chat_model_base_interruption_with_structured_schema(
        self,
    ) -> None:
        """Structured output must not retry an interrupted model call."""

        class StructuredOutput(BaseModel):
            """Minimal structured output schema."""

            answer: str

        await self._assert_chat_model_base_interruption(StructuredOutput)
