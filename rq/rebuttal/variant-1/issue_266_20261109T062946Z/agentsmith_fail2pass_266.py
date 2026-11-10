import pytest
from mle.utils.memory import LanceDBMemory
import tempfile
import os


@pytest.fixture(scope="module")
def memory_instance():
    # Create a temporary directory for LanceDB storage
    with tempfile.TemporaryDirectory() as tmpdir:
        mem = LanceDBMemory(project_path=tmpdir, table_name="test_memory")
        yield mem


def test_list_all_keys_and_get(memory_instance):
    mem = memory_instance

    # Clear table if exists
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    # Add sample data
    sample_data = [
        {"id": "id1", "text": "hello world", "metadata": {"tag": "greeting"}},
        {"id": "id2", "text": "foo bar", "metadata": {"tag": "test"}},
        {"id": "id3", "text": "lorem ipsum", "metadata": {"tag": "latin"}},
    ]
    mem.client.create_table(mem.table_name, data=sample_data)
    mem.client.open_table(mem.table_name).create_fts_index("id")

    # Test list_all_keys returns all ids
    keys = mem.list_all_keys()
    assert isinstance(keys, list)
    assert set(keys) == {"id1", "id2", "id3"}

    # Test get returns correct record by id
    rec = mem.get("id2")
    assert isinstance(rec, list)
    assert len(rec) == 1
    assert rec[0]["id"] == "id2"
    assert rec[0]["text"] == "foo bar"
    assert rec[0]["metadata"]["tag"] == "test"

    # Test get returns empty list for missing id
    rec_none = mem.get("nonexistent")
    assert isinstance(rec_none, list)
    assert rec_none == []


def test_get_by_metadata_and_delete_by_metadata(memory_instance):
    mem = memory_instance

    # Clear table if exists
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    # Add sample data with metadata
    sample_data = [
        {"id": "a1", "text": "data one", "metadata": {"category": "alpha"}},
        {"id": "a2", "text": "data two", "metadata": {"category": "beta"}},
        {"id": "a3", "text": "data three", "metadata": {"category": "alpha"}},
    ]
    mem.client.create_table(mem.table_name, data=sample_data)
    mem.client.open_table(mem.table_name).create_fts_index("id")

    # Test get_by_metadata returns correct filtered records
    alpha_records = mem.get_by_metadata("category", "alpha")
    assert isinstance(alpha_records, list)
    assert len(alpha_records) == 2
    ids = {r["id"] for r in alpha_records}
    assert ids == {"a1", "a3"}

    # Test delete_by_metadata removes records with given metadata
    success = mem.delete_by_metadata("category", "beta")
    assert success is True

    # After deletion, records with category beta should be gone
    remaining = mem.list_all_keys()
    assert "a2" not in remaining
    assert "a1" in remaining and "a3" in remaining


def test_delete_and_drop(memory_instance):
    mem = memory_instance

    # Clear table if exists
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    # Add sample data
    sample_data = [
        {"id": "x1", "text": "delete me", "metadata": {"flag": "remove"}},
        {"id": "x2", "text": "keep me", "metadata": {"flag": "keep"}},
    ]
    mem.client.create_table(mem.table_name, data=sample_data)
    mem.client.open_table(mem.table_name).create_fts_index("id")

    # Delete one record by id
    deleted = mem.delete("x1")
    assert deleted is True

    keys_after_delete = mem.list_all_keys()
    assert "x1" not in keys_after_delete
    assert "x2" in keys_after_delete

    # Drop the entire table
    dropped = mem.drop()
    assert dropped is True

    # Table should no longer exist
    assert mem.table_name not in mem.client.table_names()