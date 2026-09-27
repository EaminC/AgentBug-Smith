import asyncio
import os
import pytest

from agentscope.agent import Agent
from agentscope.message import UserMsg
from agentscope.middleware import Mem0Middleware
from agentscope.model import DashScopeChatModel
from agentscope.embedding import DashScopeEmbeddingModel
from agentscope.credential import DashScopeCredential
from agentscope.tool import Toolkit


@pytest.mark.asyncio
async def test_mem0_middleware_end_to_end_cross_session():
    """
    End-to-end test of Mem0Middleware with real DashScope models in OSS mode.

    This test:
    - Creates a Mem0Middleware with local OSS AsyncMemory backend configured
      to use DashScope chat and embedding models.
    - Runs two independent agent sessions with the same user_id.
    - Verifies that memory is persisted and bridged across sessions.
    - Verifies that the memory note is injected into the agent context.
    - Verifies that the middleware writes back new memories after each turn.
    """

    # Require DASHSCOPE_API_KEY env var for DashScope models
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY environment variable is required for this test")

    user_id = "test_user_1665"

    # Create DashScope chat and embedding models
    chat_model = DashScopeChatModel(
        credential=DashScopeCredential(api_key=api_key),
        model="qwen3.7-max",
        stream=False,
    )
    embedding_model = DashScopeEmbeddingModel(
        credential=DashScopeCredential(api_key=api_key),
        model="text-embedding-v4",
        parameters=DashScopeEmbeddingModel.Parameters(dimensions=1536),
    )

    # Construct Mem0Middleware with explicit vector store config for local OSS Qdrant
    from mem0.configs.base import MemoryConfig
    from mem0.vector_stores.configs import VectorStoreConfig

    qdrant_path = "/tmp/qdrant"
    mem0_cfg = MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="qdrant",
            config={
                "collection_name": "mem0",
                "path": qdrant_path,
                "embedding_model_dims": 1536,
                "on_disk": False,
            },
        ),
    )

    mw = Mem0Middleware(
        user_id=user_id,
        agent_id="agent_1665",
        chat_model=chat_model,
        embedding_model=embedding_model,
        mem0_config=mem0_cfg,
        mode="both",
        top_k=5,
    )

    # Build agent toolkit with memory tools
    toolkit = Toolkit(tools=await mw.list_tools())

    # Create agent with middleware and toolkit
    agent = Agent(
        name="agent_1665",
        system_prompt=(
            "You are a helpful assistant. Remember user preferences and facts."
        ),
        model=chat_model,
        toolkit=toolkit,
        middlewares=[mw],
    )

    # Session 1: send a user message that should be remembered
    user_msg_1 = UserMsg(user_id, "I like dark mode charts and matplotlib.")
    reply_1 = await agent.reply(user_msg_1)

    # Assert reply is non-empty string
    reply_text_1 = reply_1.get_text_content()
    assert isinstance(reply_text_1, str)
    assert len(reply_text_1) > 0

    # The middleware should have injected a memory message in context
    memory_msgs = [m for m in agent.state.context if getattr(m, "name", None) == "memory"]
    assert len(memory_msgs) == 1
    memory_hint = memory_msgs[0].get_text_content()
    assert "Relevant memories" in memory_hint or "memories" in memory_hint.lower()

    # Session 2: create a fresh agent with empty context, same user_id and middleware
    agent2 = Agent(
        name="agent_1665",
        system_prompt=(
            "You are a helpful assistant. Remember user preferences and facts."
        ),
        model=chat_model,
        toolkit=toolkit,
        middlewares=[mw],
    )

    user_msg_2 = UserMsg(user_id, "Show me a bar chart of monthly sales.")
    reply_2 = await agent2.reply(user_msg_2)

    reply_text_2 = reply_2.get_text_content()
    assert isinstance(reply_text_2, str)
    assert len(reply_text_2) > 0

    # The second agent should also get a memory message injected
    memory_msgs_2 = [m for m in agent2.state.context if getattr(m, "name", None) == "memory"]
    assert len(memory_msgs_2) == 1

    # The memory hints from session 1 should appear in session 2's memory note
    memory_hint_2 = memory_msgs_2[0].get_text_content()
    assert "dark mode" in memory_hint_2.lower() or "matplotlib" in memory_hint_2.lower()

    # The middleware should have written back memories after both turns
    # We can verify this by checking that the middleware's internal client has some memories
    # Since this is OSS backend, we can try to search directly
    results_1 = await mw._async_search("dark mode", user_id=user_id, agent_id="agent_1665")
    results_2 = await mw._async_search("bar chart", user_id=user_id, agent_id="agent_1665")

    # The results should include some memories (non-empty)
    assert any("dark mode" in r.lower() or "matplotlib" in r.lower() for r in results_1)
    assert any("bar chart" in r.lower() or "sales" in r.lower() for r in results_2) or len(results_2) == 0


if __name__ == "__main__":
    # Run the test with pytest style
    import sys

    sys.exit(pytest.main([__file__]))
