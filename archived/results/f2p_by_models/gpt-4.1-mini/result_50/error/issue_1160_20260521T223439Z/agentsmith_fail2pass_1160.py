import os
import pytest

from agentscope.memory._long_term_memory._mem0._mem0_long_term_memory import Mem0LongTermMemory


@pytest.mark.asyncio
async def test_mem0longtermmemory_init_and_record():
    # We test that Mem0LongTermMemory requires at least one identifier,
    # and that record returns a dict (not None).
    # This test should fail on buggy code (missing validation or wrong record return)
    # and pass on fixed code.

    # Create dummy model and embedding model classes to satisfy constructor
    class DummyModel:
        def __init__(self):
            # Use environment variable for API key if needed
            self.api_key = os.getenv("OPENAI_API_KEY")

    class DummyEmbeddingModel:
        pass

    # Create dummy vector store config
    class DummyVectorStoreConfig:
        pass

    # We test that missing all identifiers raises ValueError
    with pytest.raises(ValueError):
        Mem0LongTermMemory(
            agent_name=None,
            user_name=None,
            run_name=None,
            model=DummyModel(),
            embedding_model=DummyEmbeddingModel(),
        )

    # Provide at least one identifier
    mem = Mem0LongTermMemory(
        agent_name="agent1",
        user_name=None,
        run_name=None,
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )

    # The record method is async and returns a dict on fixed code
    # We call record with minimal dummy messages and check return type
    dummy_messages = [
        {
            "role": "user",
            "content": "Hello world",
        }
    ]

    result = await mem.record(dummy_messages)
    assert isinstance(result, dict), "record should return a dict"


@pytest.mark.asyncio
async def test_mem0longtermmemory_record_returns_dict_not_none():
    # This test ensures that record returns a dict, not None.
    # On buggy code, record returns None, so this test fails.
    # On fixed code, record returns dict, so this test passes.

    class DummyModel:
        def __init__(self):
            self.api_key = os.getenv("OPENAI_API_KEY")

    class DummyEmbeddingModel:
        pass

    class DummyVectorStoreConfig:
        pass

    mem = Mem0LongTermMemory(
        agent_name="agentX",
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )

    dummy_messages = [
        {
            "role": "user",
            "content": "Test message",
        }
    ]

    result = await mem.record(dummy_messages)
    assert result is not None, "record should not return None"
    assert isinstance(result, dict), "record should return a dict"


@pytest.mark.asyncio
async def test_mem0longtermmemory_valid_identifiers():
    # Test that providing any one of agent_name, user_name, or run_name does not raise
    class DummyModel:
        def __init__(self):
            self.api_key = os.getenv("OPENAI_API_KEY")

    class DummyEmbeddingModel:
        pass

    class DummyVectorStoreConfig:
        pass

    # agent_name only
    mem = Mem0LongTermMemory(
        agent_name="agent",
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )
    assert mem.agent_id == "agent"

    # user_name only
    mem = Mem0LongTermMemory(
        user_name="user",
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )
    assert mem.user_id == "user"

    # run_name only
    mem = Mem0LongTermMemory(
        run_name="run",
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )
    assert mem.run_id == "run"


@pytest.mark.asyncio
async def test_mem0longtermmemory_record_infer_false():
    # Test record with infer=False returns dict
    class DummyModel:
        def __init__(self):
            self.api_key = os.getenv("OPENAI_API_KEY")

    class DummyEmbeddingModel:
        pass

    class DummyVectorStoreConfig:
        pass

    mem = Mem0LongTermMemory(
        agent_name="agent",
        model=DummyModel(),
        embedding_model=DummyEmbeddingModel(),
        vector_store_config=DummyVectorStoreConfig(),
        suppress_mem0_logging=True,
    )

    dummy_messages = [
        {
            "role": "user",
            "content": "Another test",
        }
    ]

    result = await mem.record(dummy_messages, infer=False)
    assert isinstance(result, dict), "record should return a dict even with infer=False"