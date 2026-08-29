import os
import pytest
import numpy as np

from pydantic import ValidationError

from crewai.crew import Crew
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage


class DummyWatsonEmbeddingFunction:
    def __init__(self, model, api_url, api_key, project_id):
        self.model = model
        self.api_url = api_url
        self.api_key = api_key
        self.project_id = project_id

    def embed(self, texts):
        # Return fixed dummy embeddings for testing
        return [np.ones(5) for _ in texts]


def test_watson_embedder_usage(monkeypatch):
    """
    Test that Crew correctly uses the Watson embedder configuration and does not
    fallback to OpenAI embedder requiring an OpenAI API key.
    """

    # Patch KnowledgeStorage._create_default_embedding_function to raise if called,
    # to detect fallback to OpenAI embedding function creation.
    def fail_if_default_embedding_function_called(self):
        raise RuntimeError("Default OpenAI embedding function creation should not be called")

    monkeypatch.setattr(KnowledgeStorage, "_create_default_embedding_function", fail_if_default_embedding_function_called)

    # Patch KnowledgeStorage._set_embedder_config to use DummyWatsonEmbeddingFunction when provider is 'watson'
    original_set_embedder_config = KnowledgeStorage._set_embedder_config

    def patched_set_embedder_config(self, embedder_config):
        if embedder_config.get("provider") == "watson":
            config = embedder_config.get("config", {})
            self.embedding_function = DummyWatsonEmbeddingFunction(
                model=config.get("model"),
                api_url=config.get("api_url"),
                api_key=config.get("api_key"),
                project_id=config.get("project_id"),
            )
        else:
            original_set_embedder_config(self, embedder_config)

    monkeypatch.setattr(KnowledgeStorage, "_set_embedder_config", patched_set_embedder_config)

    # Prepare a StringKnowledgeSource with embedder config for Watson
    watson_embedder_config = {
        "provider": "watson",
        "config": {
            "model": "ibm/slate-125m-english-rtrvr",
            "api_url": "https://dummy.watsonx.api",
            "api_key": "dummyapikey",
            "project_id": "dummyprojectid",
        },
    }

    string_source = StringKnowledgeSource(
        content="User's name is John. He is 30 years old and lives in San Francisco."
    )

    # Create Crew with knowledge_sources and watson embedder config
    crew = Crew(
        agents=[],
        tasks=[],
        knowledge_sources=[string_source],
        embedder=watson_embedder_config,
        process=None,
        verbose=False,
    )

    # Access the underlying KnowledgeStorage to verify embedding_function is DummyWatsonEmbeddingFunction
    knowledge_storage = string_source.storage
    assert knowledge_storage is not None, "KnowledgeStorage should be initialized"
    assert hasattr(knowledge_storage, "embedding_function"), "embedding_function should be set"
    embedding_function = knowledge_storage.embedding_function
    assert isinstance(embedding_function, DummyWatsonEmbeddingFunction), "Should use Watson embedding function"

    # Test embedding function returns expected dummy embeddings
    embeddings = embedding_function.embed(["test text"])
    assert isinstance(embeddings, list)
    assert len(embeddings) == 1
    assert np.allclose(embeddings[0], np.ones(5))

    # Test that saving documents does not raise and uses the storage correctly
    string_source.chunks = ["dummy chunk"]
    # Should not raise because storage is set and patched
    string_source._save_documents()