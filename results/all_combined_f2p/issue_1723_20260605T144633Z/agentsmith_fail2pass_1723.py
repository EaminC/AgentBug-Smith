import os
import shutil
import pytest

from src.crewai.memory.storage import rag_storage
from src.crewai.utilities.paths import db_storage_path


def test_rag_storage_reset_does_not_raise_and_cleans_dir():
    """
    Test that calling reset on RAGStorage for short-term memory does not raise disk I/O errors,
    and properly cleans up the storage directory and resets internal state.
    This test should fail on the buggy codebase due to disk I/O error,
    and pass on the fixed codebase.
    """
    # Create instance of RAGStorage for short_term memory type
    storage = rag_storage.RAGStorage(type="short_term")

    # Setup: simulate that the storage directory exists with some files
    base_path = os.path.join(db_storage_path(), "short_term")
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path, exist_ok=True)
    dummy_file = os.path.join(base_path, "dummy.db")
    with open(dummy_file, "w") as f:
        f.write("dummy content")

    # Assign dummy app and collection to simulate initialized state
    # Import chromadb directly to create PersistentClient instance
    import chromadb
    from chromadb.config import Settings

    storage.app = chromadb.PersistentClient(
        path=base_path,
        settings=Settings(allow_reset=True),
    )
    storage.collection = None

    # Call reset and assert no exceptions
    try:
        storage.reset()
    except Exception as e:
        pytest.fail(f"Reset raised an unexpected exception: {e}")

    # After reset, the storage directory should be removed
    assert not os.path.exists(base_path), "Storage directory was not removed on reset"

    # The internal app and collection should be None after reset
    assert storage.app is None, "Storage app was not set to None after reset"
    assert storage.collection is None, "Storage collection was not set to None after reset"
