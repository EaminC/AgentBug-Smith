import unittest
from unittest.mock import patch, MagicMock
import tempfile
from mle.utils.memory import LanceDBMemory


class TestLanceDBMemoryManageAPI(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to simulate project_path
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = self.temp_dir.name

        # Patch get_config to avoid NotImplementedError in LanceDBMemory.__init__
        patcher_config = patch('mle.utils.memory.get_config', return_value={"platform": "OpenAI", "api_key": "dummy"})
        self.addCleanup(patcher_config.stop)
        self.mock_get_config = patcher_config.start()

        # Patch lancedb.connect to avoid real DB connection
        patcher_connect = patch('mle.utils.memory.lancedb.connect')
        self.addCleanup(patcher_connect.stop)
        self.mock_connect = patcher_connect.start()

        # Setup a mock client and mock table
        self.mock_client = MagicMock()
        self.mock_connect.return_value = self.mock_client
        self.mock_table = MagicMock()
        self.mock_client.open_table.return_value = self.mock_table

        # Setup mock for get_registry().get("openai").create(...)
        patcher_registry = patch('mle.utils.memory.get_registry')
        self.addCleanup(patcher_registry.stop)
        self.mock_registry = patcher_registry.start()
        mock_openai = MagicMock()
        mock_openai.create.return_value = MagicMock()
        self.mock_registry.return_value.get.return_value = mock_openai

        # Instantiate LanceDBMemory with dummy project_path
        self.mem = LanceDBMemory(project_path=self.project_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_list_all_keys(self):
        # Setup mock for table.search(query_type="fts").to_list()
        self.mock_table.search.return_value.to_list.return_value = [
            {"id": "id1", "metadata": {"key": "value1"}},
            {"id": "id2", "metadata": {"key": "value2"}},
        ]

        keys = self.mem.list_all_keys()
        self.mock_client.open_table.assert_called_once_with(self.mem.table_name)
        self.mock_table.search.assert_called_once_with(query_type="fts")
        self.mock_table.search.return_value.to_list.assert_called_once()
        self.assertEqual(keys, ["id1", "id2"])

    def test_get_existing_record(self):
        record_id = "id123"
        expected_record = [{"id": record_id, "metadata": {"foo": "bar"}}]
        # Setup mock for table.search(query_type="fts").where(...).limit(1).to_list()
        mock_search = MagicMock()
        mock_search.where.return_value.limit.return_value.to_list.return_value = expected_record
        self.mock_table.search.return_value = mock_search

        result = self.mem.get(record_id)
        self.mock_client.open_table.assert_called_once_with(self.mem.table_name)
        self.mock_table.search.assert_called_once_with(query_type="fts")
        mock_search.where.assert_called_once_with(f"id = '{record_id}'")
        mock_search.where.return_value.limit.assert_called_once_with(1)
        mock_search.where.return_value.limit.return_value.to_list.assert_called_once()
        self.assertEqual(result, expected_record)

    def test_get_nonexistent_record(self):
        record_id = "nonexistent"
        # Setup mock to return empty list
        mock_search = MagicMock()
        mock_search.where.return_value.limit.return_value.to_list.return_value = []
        self.mock_table.search.return_value = mock_search

        result = self.mem.get(record_id)
        self.assertEqual(result, [])

    def test_get_by_metadata(self):
        key = "category"
        value = "test"
        expected_records = [
            {"id": "id1", "metadata": {key: value}},
            {"id": "id2", "metadata": {key: value}},
        ]
        mock_search = MagicMock()
        mock_search.where.return_value.limit.return_value.to_list.return_value = expected_records
        self.mock_table.search.return_value = mock_search

        results = self.mem.get_by_metadata(key, value, n_results=2)
        self.mock_client.open_table.assert_called_once_with(self.mem.table_name)
        self.mock_table.search.assert_called_once_with(query_type="fts")
        mock_search.where.assert_called_once_with(f"metadata.{key} = '{value}'")
        mock_search.where.return_value.limit.assert_called_once_with(2)
        mock_search.where.return_value.limit.return_value.to_list.assert_called_once()
        self.assertEqual(results, expected_records)

    def test_delete_by_metadata(self):
        key = "type"
        value = "obsolete"
        self.mock_table.delete.return_value = True

        result = self.mem.delete_by_metadata(key, value)
        self.mock_client.open_table.assert_called_once_with(self.mem.table_name)
        self.mock_table.delete.assert_called_once_with(f"metadata.{key} = '{value}'")
        self.assertTrue(result)

    def test_drop_table(self):
        self.mock_client.drop_table.return_value = True
        result = self.mem.drop()
        self.mock_client.drop_table.assert_called_once_with(self.mem.table_name)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
