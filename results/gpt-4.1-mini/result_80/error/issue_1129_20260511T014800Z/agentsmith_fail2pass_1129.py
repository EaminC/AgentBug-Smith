import os
import asyncio
import unittest

from agentscope.memory._long_term_memory._mem0._mem0_utils import Mem0LongTermMemory
from agentscope.model.ollama import OllamaChatModel, OllamaTextEmbedding
from agentscope.message import Msg


class TestLongTermMemory(unittest.TestCase):
    def test_record_and_retrieve(self):
        long_term_memory = Mem0LongTermMemory(
            agent_name="Friday",
            user_name="user_123",
            model=OllamaChatModel(
                "qwen3:0.6b",
                True,
                host="http://host.docker.internal:11434",
                api_key=os.getenv("OPENAI_API_KEY"),
            ),
            embedding_model=OllamaTextEmbedding(
                "qwen3-embedding:0.6b",
                1024,
                host="http://host.docker.internal:11434",
                api_key=os.getenv("OPENAI_API_KEY"),
            ),
            on_disk=False,
        )

        async def test():
            await long_term_memory.record([Msg(name="user", content="我喜欢住民宿", role="user")])
            retrieve_result = await long_term_memory.retrieve([Msg(name="user", content="我的住宿偏好", role="user")])
            return retrieve_result

        result = asyncio.run(test())

        assert result is not None
        if hasattr(result, "content"):
            assert isinstance(result.content, str)
            assert len(result.content) > 0
        else:
            assert len(result) > 0


if __name__ == "__main__":
    unittest.main()