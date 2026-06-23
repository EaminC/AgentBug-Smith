import tempfile
from unittest.mock import MagicMock, patch

from mle.utils.memory import LanceDBMemory


@patch('mle.utils.memory.get_registry')
@patch('mle.utils.memory.get_config')
def test_list_all_keys(mock_get_config, mock_get_registry):
    mock_get_config.return_value = {"platform": "OpenAI", "api_key": "dummy_key"}
    mock_get_registry.return_value.get.return_value.create.return_value = MagicMock()

    with patch('lancedb.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.table_names.return_value = []
        mock_table = MagicMock()
        mock_client.open_table.return_value = mock_table
        mock_table.search.return_value.to_list.return_value = [
            {"id": "id1"},
            {"id": "id2"}
        ]

        tmpdir = tempfile.mkdtemp()
        try:
            memory = LanceDBMemory(project_path=tmpdir)
            keys = memory.list_all_keys()
            assert keys == ["id1", "id2"]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


@patch('mle.utils.memory.get_registry')
@patch('mle.utils.memory.get_config')
def test_get(mock_get_config, mock_get_registry):
    mock_get_config.return_value = {"platform": "OpenAI", "api_key": "dummy_key"}
    mock_get_registry.return_value.get.return_value.create.return_value = MagicMock()
    
    with patch('lancedb.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.table_names.return_value = []
        mock_table = MagicMock()
        mock_client.open_table.return_value = mock_table
        mock_table.search.return_value.where.return_value.limit.return_value.to_list.return_value = [
            {"id": "test-id", "data": "test"}
        ]

        tmpdir = tempfile.mkdtemp()
        try:
            memory = LanceDBMemory(project_path=tmpdir)
            result = memory.get("test-id")
            assert result == [{"id": "test-id", "data": "test"}]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


@patch('mle.utils.memory.get_registry')
@patch('mle.utils.memory.get_config')
def test_get_by_metadata(mock_get_config, mock_get_registry):
    mock_get_config.return_value = {"platform": "OpenAI", "api_key": "dummy_key"}
    mock_get_registry.return_value.get.return_value.create.return_value = MagicMock()
    
    with patch('lancedb.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.table_names.return_value = []
        mock_table = MagicMock()
        mock_client.open_table.return_value = mock_table
        mock_table.search.return_value.where.return_value.limit.return_value.to_list.return_value = [
            {"id": "1", "metadata": {"key": "value"}}
        ]

        tmpdir = tempfile.mkdtemp()
        try:
            memory = LanceDBMemory(project_path=tmpdir)
            result = memory.get_by_metadata("key", "value")
            assert result == [{"id": "1", "metadata": {"key": "value"}}]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


@patch('mle.utils.memory.get_registry')
@patch('mle.utils.memory.get_config')
def test_delete_by_metadata(mock_get_config, mock_get_registry):
    mock_get_config.return_value = {"platform": "OpenAI", "api_key": "dummy_key"}
    mock_get_registry.return_value.get.return_value.create.return_value = MagicMock()
    
    with patch('lancedb.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.table_names.return_value = []
        mock_table = MagicMock()
        mock_client.open_table.return_value = mock_table
        mock_table.delete.return_value = True

        tmpdir = tempfile.mkdtemp()
        try:
            memory = LanceDBMemory(project_path=tmpdir)
            result = memory.delete_by_metadata("key", "value")
            assert result is True
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


@patch('mle.utils.memory.get_registry')
@patch('mle.utils.memory.get_config')
def test_integration(mock_get_config, mock_get_registry):
    mock_get_config.return_value = {"platform": "OpenAI", "api_key": "dummy_key"}
    mock_get_registry.return_value.get.return_value.create.return_value = MagicMock()
    
    with patch('lancedb.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.table_names.return_value = []
        mock_table = MagicMock()
        mock_client.open_table.return_value = mock_table
        mock_client.create_table.return_value = mock_table
        mock_table.add.return_value = None
        mock_table.search.return_value.to_list.return_value = [{"id": "id1"}, {"id": "id2"}]
        mock_table.search.return_value.where.return_value.limit.return_value.to_list.return_value = [
            {"id": "id1", "data": "test"}
        ]
        mock_table.delete.return_value = True

        tmpdir = tempfile.mkdtemp()
        try:
            memory = LanceDBMemory(project_path=tmpdir)
            memory.add([{"id": "id1", "text": "hello"}])
            keys = memory.list_all_keys()
            assert keys == ["id1", "id2"]
            record = memory.get("id1")
            assert record == [{"id": "id1", "data": "test"}]
            deleted = memory.delete("id1")
            assert deleted is True
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)