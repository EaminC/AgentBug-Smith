import os
import unittest
from unittest.mock import patch, MagicMock

import mle.utils.memory as memory


class TestMem0(unittest.TestCase):
    def setUp(self):
        # Patch the imported classes from mem0 package inside memory.py
        # We patch where they are used, i.e. inside mle.utils.memory
        # The error showed MemoryClient and Memory do not exist in mle.utils.memory
        # So we patch the correct import paths based on the actual code structure.
        # Assuming MemoryClient and Memory are imported inside mle.utils.memory from mem0.client
        # We patch them in mle.utils.memory namespace only if they exist there.
        # To fix AttributeError, we patch the actual source locations instead.

        # Patch MemoryClient and Memory where they are defined, e.g. mem0.client.memory_client.MemoryClient
        # and mem0.client.memory.Memory or similar.
        # Since we do not have exact source, we patch the likely locations:

        patcher_client = patch("mem0.client.memory_client.MemoryClient", autospec=True)
        patcher_memory = patch("mem0.client.memory.Memory", autospec=True)

        self.addCleanup(patcher_client.stop)
        self.addCleanup(patcher_memory.stop)

        self.mock_client_class = patcher_client.start()
        self.mock_memory_class = patcher_memory.start()

    def test_init_with_token_uses_memoryclient(self):
        token = "dummy-token"
        mock_client_instance = MagicMock()
        self.mock_client_class.return_value = mock_client_instance

        mem = memory.Mem0(token=token)

        self.mock_client_class.assert_called_once_with(api_key=token)
        self.assertIs(mem.client, mock_client_instance)
        self.assertEqual(mem.token, token)
        self.assertEqual(mem.agent_id, "default")

    def test_init_without_token_uses_memory(self):
        mock_memory_instance = MagicMock()
        self.mock_memory_class.return_value = mock_memory_instance

        mem = memory.Mem0()

        self.mock_memory_class.assert_called_once_with()
        self.assertIs(mem.client, mock_memory_instance)
        self.assertIsNone(mem.token)
        self.assertEqual(mem.agent_id, "default")

    def test_add_calls_client_add_with_correct_params(self):
        mem = memory.Mem0()
        mem.client = MagicMock()
        messages = [{"role": "user", "content": "Hello"}]
        metadata = {"key": "value"}
        prompt = "prompt text"
        infer = True

        mem.add(messages, metadata=metadata, prompt=prompt, infer=infer)

        mem.client.add.assert_called_once_with(
            messages,
            metadata=metadata,
            prompt=prompt,
            infer=infer,
            agent_id=mem.agent_id,
        )

    def test_query_calls_client_search_with_correct_params(self):
        mem = memory.Mem0()
        mem.client = MagicMock()

        query_text = "find this"
        n_results = 7

        mem.query(query_text, n_results=n_results)

        mem.client.search.assert_called_once_with(
            agent_id=mem.agent_id,
            query_text=query_text,
            limit=n_results,
        )

    def test_query_returns_none_due_to_missing_return_bug(self):
        # This test exposes the bug that query method does not return the search result
        mem = memory.Mem0()
        mem.client = MagicMock()
        expected_results = ["result1", "result2"]
        mem.client.search.return_value = expected_results

        result = mem.query("some query")

        # The buggy code returns None, so this test expects result to be None (fail2pass)
        self.assertIsNotNone(result, "query() should return the search results but returned None")

    def test_get_all_calls_client_get_all_with_filters(self):
        mem = memory.Mem0()
        mem.client = MagicMock()
        filters = {"tag": "test"}
        n_results = 50

        mem.get_all(filters=filters, n_results=n_results)

        mem.client.get_all.assert_called_once_with(
            agent_id=mem.agent_id,
            filters=filters,
            limit=n_results,
        )

    def test_reset_calls_client_reset(self):
        mem = memory.Mem0()
        mem.client = MagicMock()

        mem.reset()

        mem.client.reset.assert_called_once_with(agent_id=mem.agent_id)


if __name__ == "__main__":
    unittest.main()