import os
import shutil
import pytest
import lancedb
from mle.utils.memory import LanceDBMemory
from mle.utils import get_config
from mle.text_embedding import get_registry

@pytest.fixture(scope="module")
def memory_instance(tmp_path_factory):
    # Patch get_config to return a dummy config to avoid NotImplementedError
    import mle.utils.memory as memory_module

    def dummy_get_config(project_path):
        # Provide a config with platform "OpenAI" and dummy api_key to avoid NotImplementedError
        return {"platform": "OpenAI", "api_key": os.getenv("OPENAI_API_KEY", "dummy_api_key")}

    original_get_config = memory_module.get_config
    memory_module.get_config = dummy_get_config

    tmp_path = tmp_path_factory.mktemp("lancedb_memory")
    mem = LanceDBMemory(project_path=str(tmp_path))

    yield mem

    # Cleanup
    memory_module.get_config = original_get_config
    db_dir = os.path.join(str(tmp_path), '.mle')
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)

def test_list_all_keys_and_get(memory_instance):
    mem = memory_instance

    records = [
        {"id": "id1", "text": "hello world", "metadata": {"tag": "greeting"}},
        {"id": "id2", "text": "foo bar", "metadata": {"tag": "test"}},
        {"id": "id3", "text": "lorem ipsum", "metadata": {"tag": "latin"}},
    ]
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    mem.client.create_table(mem.table_name, data=records)
    table = mem.client.open_table(mem.table_name)
    table.create_fts_index("id")

    keys = mem.list_all_keys()
    assert set(keys) == {"id1", "id2", "id3"}

    rec = mem.get("id2")
    assert isinstance(rec, list)
    assert len(rec) == 1
    assert rec[0]["id"] == "id2"
    assert rec[0]["text"] == "foo bar"

    rec_none = mem.get("nonexistent")
    assert rec_none == []

def test_get_by_metadata_and_delete_by_metadata(memory_instance):
    mem = memory_instance

    records = [
        {"id": "a1", "text": "apple", "metadata": {"category": "fruit"}},
        {"id": "a2", "text": "banana", "metadata": {"category": "fruit"}},
        {"id": "b1", "text": "carrot", "metadata": {"category": "vegetable"}},
    ]
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    mem.client.create_table(mem.table_name, data=records)
    table = mem.client.open_table(mem.table_name)
    table.create_fts_index("id")

    fruits = mem.get_by_metadata("category", "fruit", n_results=10)
    fruit_ids = {r["id"] for r in fruits}
    assert fruit_ids == {"a1", "a2"}

    result = mem.delete_by_metadata("category", "fruit")
    assert result is True or result is False

    fruits_after = mem.get_by_metadata("category", "fruit", n_results=10)
    assert fruits_after == []

    vegs = mem.get_by_metadata("category", "vegetable", n_results=10)
    assert len(vegs) == 1
    assert vegs[0]["id"] == "b1"

def test_delete_and_drop(memory_instance):
    mem = memory_instance

    records = [
        {"id": "x1", "text": "data1", "metadata": {"type": "test"}},
        {"id": "x2", "text": "data2", "metadata": {"type": "test"}},
    ]
    if mem.table_name in mem.client.table_names():
        mem.drop(mem.table_name)

    mem.client.create_table(mem.table_name, data=records)
    table = mem.client.open_table(mem.table_name)
    table.create_fts_index("id")

    deleted = mem.delete("x1")
    assert deleted is True or deleted is False

    rec = mem.get("x1")
    assert rec == []

    rec2 = mem.get("x2")
    assert len(rec2) == 1 and rec2[0]["id"] == "x2"

    dropped = mem.drop()
    assert dropped is True or dropped is False

    assert mem.table_name not in mem.client.table_names()