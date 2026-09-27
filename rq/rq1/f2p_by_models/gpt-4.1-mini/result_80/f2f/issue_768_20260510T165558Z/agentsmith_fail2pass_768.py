import os
import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime
from collections import OrderedDict
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, execute_python_code, execute_shell_command


class TestVLLMTokenUsage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.toolkit = Toolkit()
        self.toolkit.register_tool_function(execute_python_code)
        self.toolkit.register_tool_function(execute_shell_command)

    async def test_vllm_model_token_usage_in_chat_response(self):
        # Prepare dummy async generator to simulate streaming response with token usage info
        async def dummy_stream():
            class DummyChoiceDelta:
                def __init__(self):
                    self.content = "Hello"
                    self.reasoning_content = None
                    self.tool_calls = None

            class DummyChoice:
                def __init__(self):
                    self.delta = DummyChoiceDelta()

            class DummyChunk:
                def __init__(self):
                    self.choices = [DummyChoice()]
                    # usage is a dict with keys as strings to simulate VLLM style
                    self.usage = {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    }

            yield DummyChunk()

        agent = ReActAgent(
            name="Friday",
            sys_prompt="You're a helpful assistant named Friday.",
            model=OpenAIChatModel(
                model_name="qwen3-coder-30b-a3b-instruct",
                api_key=os.getenv("OPENAI_API_KEY"),
                stream=True,
                client_args={"base_url": os.getenv("OPENAI_BASE_URL")},
            ),
            formatter=OpenAIChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=self.toolkit,
        )

        # Patch the instance's client attribute's chat.completions.create coroutine method
        async def async_create(*args, **kwargs):
            class DummyResponse:
                def __aiter__(self_inner):
                    return dummy_stream()

                async def __aenter__(self_inner):
                    return self_inner

                async def __aexit__(self_inner, exc_type, exc, tb):
                    pass

            return DummyResponse()

        # Patch the client attribute's chat.completions.create method to return dummy response
        with patch.object(
            agent.model.client.chat.completions,
            "create",
            new=AsyncMock(side_effect=async_create),
        ):
            start_datetime = datetime.now()
            response = await agent.model.client.chat.completions.create()
            responses = []
            # We expect the _parse_openai_stream_response to yield ChatResponse with usage populated correctly
            async for chat_response in agent.model._parse_openai_stream_response(
                start_datetime, response
            ):
                responses.append(chat_response)

            # Assert that at least one response was yielded
            self.assertTrue(len(responses) > 0)

            # Assert that usage is present and has correct fields
            usage = responses[-1].usage
            self.assertIsNotNone(usage)
            # usage is a ChatUsage object with attributes input_tokens and output_tokens
            self.assertEqual(usage.input_tokens, 10)
            self.assertEqual(usage.output_tokens, 5)
            # total_tokens is not directly stored but can be inferred
            self.assertTrue(hasattr(usage, "time"))
            self.assertIsInstance(usage.time, float)


if __name__ == "__main__":
    unittest.main()