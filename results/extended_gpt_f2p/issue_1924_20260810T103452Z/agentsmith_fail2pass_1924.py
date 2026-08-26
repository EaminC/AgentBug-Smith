from unittest.async_case import IsolatedAsyncioTestCase
from typing import Any, Callable

from agentscope.agent import Agent, ContextConfig
from agentscope.message import UserMsg, AssistantMsg, HintBlock, Msg
from agentscope.model import StructuredResponse
from agentscope.tool import Toolkit
from tests.utils import MockModel


class RecordingStructuredMockModel(MockModel):
    """A mock model that records structured-output compression calls."""

    def __init__(
        self,
        *args: Any,
        fail_structured_output_times: int = 0,
        force_compression_overflow: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the recording mock model."""
        super().__init__(*args, **kwargs)
        self.recorded_structured_messages: list[list[Msg]] = []
        self._fail_structured_output_times = fail_structured_output_times
        self._force_compression_overflow = force_compression_overflow
        self._compression_count_calls = 0

    async def count_tokens(
        self,
        messages: list[Msg],
        tools: list[dict] | None,
    ) -> int:
        """Force the overflow branch when counting compression messages."""
        is_compression_count = bool(
            tools
            and tools[0].get("function", {}).get("name")
            == "generate_structured_output",
        )
        if self._force_compression_overflow and is_compression_count:
            self._compression_count_calls += 1
            if self._compression_count_calls == 1:
                return self.context_size + 1
            return 1
        return await super().count_tokens(messages, tools)

    async def _call_api_with_structured_output(
        self,
        model_name: str,
        messages: list[Msg],
        structured_model: Any,
        **kwargs: Any,
    ) -> StructuredResponse:
        """Record the structured-output call and optionally fail first."""
        self.recorded_structured_messages.append(list(messages))
        if self._fail_structured_output_times > 0:
            self._fail_structured_output_times -= 1
            raise RuntimeError("simulated compression overflow")
        return await super()._call_api_with_structured_output(
            model_name,
            messages,
            structured_model,
            **kwargs,
        )


def _has_instruction_hint(
    messages: list[Msg],
    instructions: HintBlock,
) -> bool:
    """Return True if messages contain instructions as an assistant hint."""
    for msg in messages:
        if msg.role != "assistant":
            continue
        for hint_block in msg.get_content_blocks("hint"):
            if hint_block.id == instructions.id:
                return hint_block.hint == instructions.hint
    return False


class AgentCompressContextInstructionsTest(IsolatedAsyncioTestCase):
    """Test that user-defined instructions are supported in compress_context."""

    async def test_instructions_are_injected_as_hintblock(self) -> None:
        """Instructions are injected as a HintBlock only for compression."""
        model = RecordingStructuredMockModel(context_size=100)
        agent = Agent(
            name="Friday",
            system_prompt="".join(["0" for _ in range(20 * 4)]),
            model=model,
            context_config=ContextConfig(
                trigger_ratio=0.7,
                reserve_ratio=0.4,
            ),
            state=agent_state_with_context(),
            toolkit=Toolkit(),
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
        instructions = HintBlock(
            hint="Keep user requirements and file paths.",
            source="user",
        )

        await agent.compress_context(instructions=instructions)

        self.assertEqual(len(model.recorded_structured_messages), 1)
        self.assertTrue(
            _has_instruction_hint(
                model.recorded_structured_messages[0],
                instructions,
            ),
        )
        # The agent's context should not contain the instructions after compression
        self.assertFalse(
            any(msg.get_content_blocks("hint") for msg in agent.state.context),
        )

    async def test_overflow_retry_keeps_instructions(self) -> None:
        """Overflow retry preserves instructions when rebuilding messages."""
        model = RecordingStructuredMockModel(
            context_size=100,
            fail_structured_output_times=1,
            force_compression_overflow=True,
        )
        agent = Agent(
            name="Friday",
            system_prompt="".join(["0" for _ in range(20 * 4)]),
            model=model,
            context_config=ContextConfig(
                trigger_ratio=0.7,
                reserve_ratio=0.4,
            ),
            state=agent_state_with_context(),
            toolkit=Toolkit(),
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
        instructions = HintBlock(
            hint="Keep the user's original success criteria.",
            source="user",
        )

        await agent.compress_context(instructions=instructions)

        self.assertEqual(len(model.recorded_structured_messages), 2)
        self.assertTrue(
            _has_instruction_hint(
                model.recorded_structured_messages[-1],
                instructions,
            ),
        )


def agent_state_with_context() -> Any:
    """Helper to create AgentState with a typical context for compression."""
    from agentscope.state import AgentState
    return AgentState(
        session_id="123",
        context=[
            UserMsg(
                "User",
                "".join(["1" for _ in range(30 * 4)]),
                id="1",
            ),
            AssistantMsg(
                "Friday",
                "".join(["2" for _ in range(10 * 4)]),
                id="2",
            ),
            UserMsg(
                "User",
                "".join(["3" for _ in range(10 * 4)]),
                id="3",
            ),
        ],
    )
