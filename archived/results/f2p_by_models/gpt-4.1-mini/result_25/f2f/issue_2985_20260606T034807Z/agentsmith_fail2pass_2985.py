import pytest
import os

from crewai.crew import Crew, Process
from crewai.agent import Agent
from crewai.memory.storage.mem0_storage import Mem0Storage
from crewai.memory import ExternalMemory


class DummyMemoryClient:
    def __init__(self):
        self.added_items = []

    def add(self, items, agent_id):
        # Simulate the expected behavior: items must be a list, agent_id max length 255
        if not isinstance(items, list):
            raise ValueError('Expected a list of items but got type "str".')
        if len(agent_id) > 255:
            raise ValueError("agent_id is too long. Maximum length allowed is 255 characters.")
        self.added_items.extend(items)
        return True

    def search(self, query):
        # Dummy search returns empty list
        return []


@pytest.fixture
def external_memory_patch(monkeypatch):
    # Patch Mem0Storage to use DummyMemoryClient internally
    original_init = Mem0Storage.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Replace internal client with dummy
        self.client = DummyMemoryClient()

    monkeypatch.setattr(Mem0Storage, "__init__", patched_init)
    yield
    # No unpatch needed, pytest monkeypatch handles it


def test_mem0_external_memory_adds_memory(external_memory_patch):
    # Define a simple agent that adds a memory entry
    class EchoAgent(Agent):
        def run(self, input_text: str):
            # Add memory to external memory
            self.memory.add_memory(f"Echoed: {input_text}")
            return f"Echoed: {input_text}"

    # Setup external memory with mem0 provider and short user_id
    external_memory = ExternalMemory(
        embedder_config={
            "provider": "mem0",
            "config": {"user_id": "deck"}
        }
    )

    # Create crew with external memory enabled
    crew = Crew(
        agents=[EchoAgent],
        tasks=[],
        process=Process.sequential,
        verbose=False,
        memory=True,
        external_memory=external_memory,
    )

    # Run the agent with some input
    result = crew.run("hello world")

    # Assert the result is as expected
    assert "Echoed: hello world" in result

    # Assert that memory was added to the dummy client (via patched Mem0Storage)
    mem_storage = None
    for mem in crew.memory_manager.memories:
        if isinstance(mem, Mem0Storage):
            mem_storage = mem
            break
    assert mem_storage is not None, "Mem0Storage instance not found in crew memories"

    # The dummy client should have recorded the added memory as a list
    assert isinstance(mem_storage.client.added_items, list)
    # The added memory string should be present in the added items
    found = any("Echoed: hello world" in item for item in mem_storage.client.added_items)
    assert found, "Memory string not found in added items"

    # Also test that agent_id length is within limits
    agent_id = mem_storage._get_agent_name()
    assert len(agent_id) <= 255, f"agent_id length {len(agent_id)} exceeds 255"

    # Test that no exception was raised during add_memory call


if __name__ == "__main__":
    pytest.main([__file__])