import json
import asyncio
from unittest.async_case import IsolatedAsyncioTestCase

from agentscope.message import ToolCallBlock
from agentscope.state import AgentState
from agentscope.tool import FunctionTool, Toolkit
from tests.utils import AnyString


class TestFunctionToolPlainStringReturn(IsolatedAsyncioTestCase):
    """Test that a plain function returning str works with FunctionTool."""

    async def test_sync_function_returning_plain_string(self) -> None:
        """Test wrapping a sync function that returns a plain string."""

        def get_weather(location: str) -> str:
            """Get weather information.

            Args:
                location: The location to get weather for
            """
            return f"The weather in {location} is sunny."

        toolkit = Toolkit(
            tools=[FunctionTool(get_weather)],
        )

        state = AgentState()
        tool_call = ToolCallBlock(
            id="test_weather",
            name="get_weather",
            input=json.dumps({"location": "Chengdu"}),
        )

        chunks = []
        response = None
        async for result in toolkit.call_tool(tool_call, state):
            if isinstance(result, (list, tuple)):
                # Defensive: if bug causes unexpected iterable
                for item in result:
                    if hasattr(item, "model_dump"):
                        chunks.append(item)
            elif hasattr(result, "model_dump"):
                if getattr(result, "state", None) == "success":
                    response = result
                else:
                    chunks.append(result)

        self.assertEqual(len(chunks), 1)
        self.assertDictEqual(
            chunks[0].model_dump(),
            {
                "content": [
                    {
                        "type": "text",
                        "id": AnyString(),
                        "text": "The weather in Chengdu is sunny.",
                    },
                ],
                "state": "running",
                "is_last": True,
                "metadata": {},
                "id": AnyString(),
            },
        )

        self.assertIsNotNone(response)
        self.assertDictEqual(
            response.model_dump(),
            {
                "content": [
                    {
                        "type": "text",
                        "id": AnyString(),
                        "text": "The weather in Chengdu is sunny.",
                    },
                ],
                "state": "success",
                "metadata": {},
                "id": "test_weather",
            },
        )
