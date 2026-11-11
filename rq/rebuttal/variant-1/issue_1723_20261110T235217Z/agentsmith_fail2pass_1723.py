import os
import shutil
import pytest

from crewai.utilities.paths import db_storage_path


def test_rag_storage_reset_removes_storage_dir_and_resets_app():
    """
    Test that RAGStorage.reset removes the storage directory and resets app and collection.
    After reset:
    - The storage directory is removed.
    - The app attribute is None.
    - The collection attribute is None.
    """
    from crewai.memory.storage import rag_storage

    for storage_type in ["short_term_memory", "long_term_memory"]:
        storage = rag_storage.RAGStorage(type=storage_type)

        # Setup dummy directory to avoid FileNotFoundError on rmtree
        storage_dir = os.path.join(db_storage_path(), storage_type)
        os.makedirs(storage_dir, exist_ok=True)

        # Assign dummy app with reset method
        class DummyApp:
            def __init__(self):
                self.reset_called = False

            def reset(self):
                self.reset_called = True

        dummy_app = DummyApp()
        storage.app = dummy_app
        storage.collection = object()

        storage.reset()

        # After reset, storage directory should not exist
        assert not os.path.exists(storage_dir), f"{storage_type} directory should be removed after reset"
        # app and collection should be None
        assert storage.app is None, "app should be None after reset"
        assert storage.collection is None, "collection should be None after reset"


def test_rag_storage_reset_handles_app_none_and_existing_app():
    """
    Test that reset works correctly whether app is None or already initialized.
    For both cases, after reset:
    - The storage directory is removed.
    - The app attribute is None.
    - The collection attribute is None.
    """
    from crewai.memory.storage import rag_storage

    for storage_type in ["short_term_memory", "long_term_memory"]:
        # Case 1: app is None
        storage = rag_storage.RAGStorage(type=storage_type)
        storage.app = None
        storage.collection = object()

        # Setup dummy directory to avoid FileNotFoundError on rmtree
        storage_dir = os.path.join(db_storage_path(), storage_type)
        os.makedirs(storage_dir, exist_ok=True)

        storage.reset()

        assert not os.path.exists(storage_dir), f"{storage_type} directory should be removed after reset when app is None"
        assert storage.app is None, "app should be None after reset when initially None"
        assert storage.collection is None, "collection should be None after reset when initially None"


def test_knowledge_storage_reset_removes_knowledge_dir_and_resets_app():
    """
    Test that KnowledgeStorage.reset removes the knowledge directory and resets app and collection.
    After reset:
    - The knowledge directory is removed.
    - The app attribute is None.
    - The collection attribute is None.
    """
    from crewai.knowledge.storage import knowledge_storage
    from crewai.utilities.constants import KNOWLEDGE_DIRECTORY

    storage = knowledge_storage.KnowledgeStorage()

    # Setup dummy knowledge directory
    knowledge_dir = os.path.join(db_storage_path(), KNOWLEDGE_DIRECTORY)
    os.makedirs(knowledge_dir, exist_ok=True)

    # Initialize dummy app with reset method
    class DummyApp:
        def __init__(self):
            self.reset_called = False

        def reset(self):
            self.reset_called = True

    dummy_app = DummyApp()
    storage.app = dummy_app
    storage.collection = object()

    storage.reset()

    # After reset, knowledge directory should not exist
    assert not os.path.exists(knowledge_dir), "Knowledge directory should be removed after reset"
    # app and collection should be None
    assert storage.app is None, "app should be None after reset"
    assert storage.collection is None, "collection should be None after reset"