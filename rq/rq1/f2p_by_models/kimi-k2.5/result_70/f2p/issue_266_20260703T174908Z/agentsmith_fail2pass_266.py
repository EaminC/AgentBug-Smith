import pytest


def test_lancedb_memory_has_manage_api_methods(monkeypatch):
    """Test that LanceDBMemory has the manage API methods: list_all_keys, get, get_by_metadata, delete_by_metadata."""
    from mle.utils.memory import LanceDBMemory

    def mock_get_config(path):
        return {'platform': 'OpenAI', 'api_key': 'fake-api-key'}
    monkeypatch.setattr('mle.utils.memory.get_config', mock_get_config)

    class MockTable:
        pass

    class MockClient:
        def table_names(self):
            return []
        def open_table(self, name):
            return MockTable()
        def create_table(self, name, data):
            return MockTable()

    class MockLanceDB:
        @staticmethod
        def connect(uri):
            return MockClient()

    monkeypatch.setattr('mle.utils.memory.lancedb', MockLanceDB())

    class MockEmbedFunc:
        def create(self, **kwargs):
            return lambda texts: [[0.1] * 384 for _ in texts]

    class MockRegistry:
        def get(self, name):
            return MockEmbedFunc()

    monkeypatch.setattr('mle.utils.memory.get_registry', lambda: MockRegistry())

    mem = LanceDBMemory("/tmp/test")

    assert hasattr(mem, 'list_all_keys'), "LanceDBMemory should have list_all_keys method"
    assert hasattr(mem, 'get'), "LanceDBMemory should have get method"
    assert hasattr(mem, 'get_by_metadata'), "LanceDBMemory should have get_by_metadata method"
    assert hasattr(mem, 'delete_by_metadata'), "LanceDBMemory should have delete_by_metadata method"


def test_lancedb_memory_list_all_keys_functionality(monkeypatch):
    """Test that list_all_keys returns IDs from the table using FTS search."""
    from mle.utils.memory import LanceDBMemory

    def mock_get_config(path):
        return {'platform': 'OpenAI', 'api_key': 'fake-api-key'}
    monkeypatch.setattr('mle.utils.memory.get_config', mock_get_config)

    class MockTable:
        def search(self, query_type=None):
            return self
        def to_list(self):
            return [{'id': 'key1'}, {'id': 'key2'}, {'id': 'key3'}]

    class MockClient:
        def table_names(self):
            return ['memory']
        def open_table(self, name):
            return MockTable()

    class MockLanceDB:
        @staticmethod
        def connect(uri):
            return MockClient()

    monkeypatch.setattr('mle.utils.memory.lancedb', MockLanceDB())

    class MockEmbedFunc:
        def create(self, **kwargs):
            return lambda texts: [[0.1] * 384 for _ in texts]

    class MockRegistry:
        def get(self, name):
            return MockEmbedFunc()

    monkeypatch.setattr('mle.utils.memory.get_registry', lambda: MockRegistry())

    mem = LanceDBMemory("/tmp/test")
    keys = mem.list_all_keys()

    assert isinstance(keys, list)
    assert set(keys) == {'key1', 'key2', 'key3'}


def test_lancedb_memory_get_functionality(monkeypatch):
    """Test that get method retrieves record by ID using FTS search."""
    from mle.utils.memory import LanceDBMemory

    def mock_get_config(path):
        return {'platform': 'OpenAI', 'api_key': 'fake-api-key'}
    monkeypatch.setattr('mle.utils.memory.get_config', mock_get_config)

    class MockTable:
        def search(self, query_type=None):
            return self
        def where(self, condition):
            return self
        def limit(self, n):
            return self
        def to_list(self):
            return [{'id': 'record-123', 'text': 'test content'}]

    class MockClient:
        def table_names(self):
            return ['memory']
        def open_table(self, name):
            return MockTable()

    class MockLanceDB:
        @staticmethod
        def connect(uri):
            return MockClient()

    monkeypatch.setattr('mle.utils.memory.lancedb', MockLanceDB())

    class MockEmbedFunc:
        def create(self, **kwargs):
            return lambda texts: [[0.1] * 384 for _ in texts]

    class MockRegistry:
        def get(self, name):
            return MockEmbedFunc()

    monkeypatch.setattr('mle.utils.memory.get_registry', lambda: MockRegistry())

    mem = LanceDBMemory("/tmp/test")
    result = mem.get('record-123')

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['id'] == 'record-123'


def test_lancedb_memory_delete_by_metadata_functionality(monkeypatch):
    """Test that delete_by_metadata deletes records by metadata key-value."""
    from mle.utils.memory import LanceDBMemory

    def mock_get_config(path):
        return {'platform': 'OpenAI', 'api_key': 'fake-api-key'}
    monkeypatch.setattr('mle.utils.memory.get_config', mock_get_config)

    class MockTable:
        def delete(self, condition):
            assert 'source' in condition
            assert 'file.txt' in condition
            return True

    class MockClient:
        def table_names(self):
            return ['memory']
        def open_table(self, name):
            return MockTable()

    class MockLanceDB:
        @staticmethod
        def connect(uri):
            return MockClient()

    monkeypatch.setattr('mle.utils.memory.lancedb', MockLanceDB())

    class MockEmbedFunc:
        def create(self, **kwargs):
            return lambda texts: [[0.1] * 384 for _ in texts]

    class MockRegistry:
        def get(self, name):
            return MockEmbedFunc()

    monkeypatch.setattr('mle.utils.memory.get_registry', lambda: MockRegistry())

    mem = LanceDBMemory("/tmp/test")
    result = mem.delete_by_metadata('source', 'file.txt')

    assert result is True


def test_lancedb_memory_get_by_metadata_functionality(monkeypatch):
    """Test that get_by_metadata retrieves records by metadata key-value."""
    from mle.utils.memory import LanceDBMemory

    def mock_get_config(path):
        return {'platform': 'OpenAI', 'api_key': 'fake-api-key'}
    monkeypatch.setattr('mle.utils.memory.get_config', mock_get_config)

    class MockTable:
        def search(self, query_type=None):
            return self
        def where(self, condition):
            assert 'source' in condition
            assert 'file.txt' in condition
            return self
        def limit(self, n):
            return self
        def to_list(self):
            return [{'id': 'rec1', 'metadata': {'source': 'file.txt'}}]

    class MockClient:
        def table_names(self):
            return ['memory']
        def open_table(self, name):
            return MockTable()

    class MockLanceDB:
        @staticmethod
        def connect(uri):
            return MockClient()

    monkeypatch.setattr('mle.utils.memory.lancedb', MockLanceDB())

    class MockEmbedFunc:
        def create(self, **kwargs):
            return lambda texts: [[0.1] * 384 for _ in texts]

    class MockRegistry:
        def get(self, name):
            return MockEmbedFunc()

    monkeypatch.setattr('mle.utils.memory.get_registry', lambda: MockRegistry())

    mem = LanceDBMemory("/tmp/test")
    results = mem.get_by_metadata('source', 'file.txt')

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]['metadata']['source'] == 'file.txt'
