Reasoning:

To resolve the issue of adding Mem0 memory support, we need to do the following:

1. Implement the Mem0 class with the specified methods (add, query, evict, mem_consolidation), supporting extended metadata, structured content, conditional eviction, and memory consolidation. Since LanceDBMemory is already designed for vectorized memory management and indexing with metadata, we can extend it or wrap it accordingly.

2. Add support in the CLI `integrate` function for the Mem0 integration that asks users optionally for their Mem0 API token or uses a default community token if no input is provided.

The first location (mle/utils/memory.py) already defines LanceDBMemory as a vectorized memory interface. We will add a new class Mem0 that uses LanceDBMemory internally or extends it and implements the required interface as per the problem description.

In the CLI (mle/cli.py), we will add the new platform 'Mem0' in the selection list, prompt optionally for an API token, and store accordingly.

No other changes are necessary.

---

Patch:

# modification 1
```
<file>mle/utils/memory.py</file>
<original>import uuid
from typing import List, Dict, Optional

import lancedb
from lancedb.embeddings import get_registry

from mle.utils import get_config


class LanceDBMemory:

    def __init__(self, project_path: str):
        """
        Memory: A base class for memory and external knowledge management.
        Args:
            project_path: the path to store the data.
        """
        self.db_name = '.mle'
        self.table_name = 'memory'
        self.client = lancedb.connect(uri=self.db_name)

        config = get_config(project_path)
        if config["platform"] == "OpenAI":
            self.text_embedding = get_registry().get("openai").create(api_key=config["api_key"])
        else:
            self.text_embedding = get_registry().get("sentence-transformers").create(
            name="sentence-transformers/paraphrase-MiniLM-L6-v2"
        )

    def _open_table(self, table_name: str = None):
        """
        Open a LanceDB table by table name. (Return None if not exists)
        Args:
            table_name (Optional[str]): The name of the table. Defaults to self.table_name.
        """
        table_name = table_name or self.table_name
        try:
            table = self.client.open_table(table_name)
        except FileNotFoundError:
            return None
        return table

    def add(
            self,
            texts: List[str],
            metadata: Optional[List[Dict]] = None,
            table_name: Optional[str] = None,
            ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Adds a list of text items to the specified memory table in the database.

        Args:
            texts (List[str]): A list of text strings to be added.
            metadata (Optional[List[Dict]]): A list of metadata to be added.
            table_name (Optional[str]): The name of the table to add data to. Defaults to self.table_name.
            ids (Optional[List[str]]): A list of unique IDs for the text items.
                If not provided, random UUIDs are generated.

        Returns:
            List[str]: A list of IDs associated with the added text items.
        """
        if isinstance(texts, str):
            texts = (texts,)

        if metadata is None:
            metadata = [None, ] * len(texts)
        elif isinstance(metadata, dict):
            metadata = (metadata,)
        else:
            assert len(texts) == len(metadata)

        embeds = self.text_embedding.compute_source_embeddings(texts)

        table_name = table_name or self.table_name
        ids = ids or [str(uuid.uuid4()) for _ in range(len(texts))]

        data = [
            {
                "vector": embed,
                "text": text,
                "id": idx,
                "metadata": meta,
            } for idx, text, embed, meta in zip(ids, texts, embeds, metadata)
        ]

        if table_name not in self.client.table_names():
            table = self.client.create_table(table_name, data=data)
            table.create_fts_index("id")
        else:
            self._open_table(table_name).add(data=data)

        return ids

    def query(self, query_texts: List[str], table_name: Optional[str] = None, n_results: int = 5) -> List[List[dict]]:
        """
        Queries the specified memory table for similar text embeddings.

        Args:
            query_texts (List[str]): A list of query text strings.
            table_name (Optional[str]): The name of the table to query. Defaults to self.table_name.
            n_results (int): The maximum number of results to retrieve per query. Default is 5.

        Returns:
            List[List[dict]]: A list of results for each query text, each result being a dictionary with
            keys such as "vector", "text", and "id".
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        query_embeds = self.text_embedding.compute_source_embeddings(query_texts)

        results = [table.search(query).limit(n_results).to_list() for query in query_embeds]
        return results

    def list_all_keys(self, table_name: Optional[str] = None):
        """
        Lists all IDs in the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to list IDs from. Defaults to the instance's table name.

        Returns:
            List[str]: A list of all IDs in the table.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return [item["id"] for item in table.search(query_type="fts").to_list()]

    def get(self, record_id: str, table_name: Optional[str] = None):
        """
        Retrieves a record by its ID from the specified memory table.

        Args:
            record_id (str): The ID of the record to retrieve.
            table_name (Optional[str]): The name of the table to query. Defaults to the instance's table name.

        Returns:
            List[dict]: A list containing the matching record, or an empty list if not found.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return table.search(query_type="fts") \
            .where(f"id = '{record_id}'") \
            .limit(1).to_list()

    def get_by_metadata(self, key: str, value: str, table_name: Optional[str] = None, n_results: int = 5):
        """
        Retrieves records matching a specific metadata key-value pair.

        Args:
            key (str): The metadata key to filter by.
            value (str): The value of the metadata key to filter by.
            table_name (Optional[str]): The name of the table to query. Defaults to the instance's table name.
            n_results (int): The maximum number of results to retrieve. Defaults to 5.

        Returns:
            List[dict]: A list of records matching the metadata criteria.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return table.search(query_type="fts") \
            .where(f"metadata.{key} = '{value}'") \
            .limit(n_results).to_list()

    def delete(self, record_id: str, table_name: Optional[str] = None) -> bool:
        """
        Deletes a record from the specified memory table.

        Args:
            record_id (str): The ID of the record to delete.
            table_name (Optional[str]): The name of the table to delete the record from. Defaults to self.table_name.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        table = self._open_table(table_name)
        if table is None:
            return True

        return table.delete(f"id = '{record_id}'")

    def delete_by_metadata(self, key: str, value: str, table_name: Optional[str] = None):
        """
        Deletes records from the specified memory table based on a metadata key-value pair.

        Args:
            key (str): The metadata key to filter by.
            value (str): The value of the metadata key to filter by.
            table_name (Optional[str]): The name of the table to delete records from. Defaults to the instance's table name.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        table = self._open_table(table_name)
        if table is None:
            return True

        return table.delete(f"metadata.{key} = '{value}'")

    def drop(self, table_name: Optional[str] = None) -> bool:
        """
        Drops (deletes) the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to delete. Defaults to self.table_name.

        Returns:
            bool: True if the table was successfully dropped, False otherwise.
        """
        table_name = table_name or self.table_name
        table = self._open_table(table_name)
        if table is None:
            return True

        return self.client.drop_table(table_name)

    def count(self, table_name: Optional[str] = None) -> int:
        """
        Counts the number of records in the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to count records in. Defaults to self.table_name.

        Returns:
            int: The number of records in the table.
        """
        table = self._open_table(table_name)
        if table is None:
            return 0

        return table.count_rows()

    def reset(self) -> None:
        """
        Resets the memory by dropping the default memory table.
        """
        self.drop()
</original>
<patched>import uuid
from typing import List, Dict, Optional, Union, Any

import lancedb
from lancedb.embeddings import get_registry

from mle.utils import get_config


class LanceDBMemory:

    def __init__(self, project_path: str):
        """
        Memory: A base class for memory and external knowledge management.
        Args:
            project_path: the path to store the data.
        """
        self.db_name = '.mle'
        self.table_name = 'memory'
        self.client = lancedb.connect(uri=self.db_name)

        config = get_config(project_path)
        if config.get("platform") == "OpenAI":
            self.text_embedding = get_registry().get("openai").create(api_key=config["api_key"])
        else:
            self.text_embedding = get_registry().get("sentence-transformers").create(
                name="sentence-transformers/paraphrase-MiniLM-L6-v2"
            )

    def _open_table(self, table_name: str = None):
        """
        Open a LanceDB table by table name. (Return None if not exists)
        Args:
            table_name (Optional[str]): The name of the table. Defaults to self.table_name.
        """
        table_name = table_name or self.table_name
        try:
            table = self.client.open_table(table_name)
        except FileNotFoundError:
            return None
        return table

    def add(
            self,
            texts: List[str],
            metadata: Optional[List[Dict]] = None,
            table_name: Optional[str] = None,
            ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Adds a list of text items to the specified memory table in the database.

        Args:
            texts (List[str]): A list of text strings to be added.
            metadata (Optional[List[Dict]]): A list of metadata to be added.
            table_name (Optional[str]): The name of the table to add data to. Defaults to self.table_name.
            ids (Optional[List[str]]): A list of unique IDs for the text items.
                If not provided, random UUIDs are generated.

        Returns:
            List[str]: A list of IDs associated with the added text items.
        """
        if isinstance(texts, str):
            texts = (texts,)

        if metadata is None:
            metadata = [None, ] * len(texts)
        elif isinstance(metadata, dict):
            metadata = (metadata,)
        else:
            assert len(texts) == len(metadata)

        embeds = self.text_embedding.compute_source_embeddings(texts)

        table_name = table_name or self.table_name
        ids = ids or [str(uuid.uuid4()) for _ in range(len(texts))]

        data = [
            {
                "vector": embed,
                "text": text,
                "id": idx,
                "metadata": meta,
            } for idx, text, embed, meta in zip(ids, texts, embeds, metadata)
        ]

        if table_name not in self.client.table_names():
            table = self.client.create_table(table_name, data=data)
            table.create_fts_index("id")
        else:
            self._open_table(table_name).add(data=data)

        return ids

    def query(self, query_texts: List[str], table_name: Optional[str] = None, n_results: int = 5) -> List[List[dict]]:
        """
        Queries the specified memory table for similar text embeddings.

        Args:
            query_texts (List[str]): A list of query text strings.
            table_name (Optional[str]): The name of the table to query. Defaults to self.table_name.
            n_results (int): The maximum number of results to retrieve per query. Default is 5.

        Returns:
            List[List[dict]]: A list of results for each query text, each result being a dictionary with
            keys such as "vector", "text", and "id".
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        query_embeds = self.text_embedding.compute_source_embeddings(query_texts)

        results = [table.search(query).limit(n_results).to_list() for query in query_embeds]
        return results

    def list_all_keys(self, table_name: Optional[str] = None):
        """
        Lists all IDs in the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to list IDs from. Defaults to the instance's table name.

        Returns:
            List[str]: A list of all IDs in the table.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return [item["id"] for item in table.search(query_type="fts").to_list()]

    def get(self, record_id: str, table_name: Optional[str] = None):
        """
        Retrieves a record by its ID from the specified memory table.

        Args:
            record_id (str): The ID of the record to retrieve.
            table_name (Optional[str]): The name of the table to query. Defaults to the instance's table name.

        Returns:
            List[dict]: A list containing the matching record, or an empty list if not found.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return table.search(query_type="fts") \
            .where(f"id = '{record_id}'") \
            .limit(1).to_list()

    def get_by_metadata(self, key: str, value: str, table_name: Optional[str] = None, n_results: int = 5):
        """
        Retrieves records matching a specific metadata key-value pair.

        Args:
            key (str): The metadata key to filter by.
            value (str): The value of the metadata key to filter by.
            table_name (Optional[str]): The name of the table to query. Defaults to the instance's table name.
            n_results (int): The maximum number of results to retrieve. Defaults to 5.

        Returns:
            List[dict]: A list of records matching the metadata criteria.
        """
        table = self._open_table(table_name)
        if table is None:
            return []

        return table.search(query_type="fts") \
            .where(f"metadata.{key} = '{value}'") \
            .limit(n_results).to_list()

    def delete(self, record_id: str, table_name: Optional[str] = None) -> bool:
        """
        Deletes a record from the specified memory table.

        Args:
            record_id (str): The ID of the record to delete.
            table_name (Optional[str]): The name of the table to delete the record from. Defaults to self.table_name.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        table = self._open_table(table_name)
        if table is None:
            return True

        return table.delete(f"id = '{record_id}'")

    def delete_by_metadata(self, key: str, value: str, table_name: Optional[str] = None):
        """
        Deletes records from the specified memory table based on a metadata key-value pair.

        Args:
            key (str): The metadata key to filter by.
            value (str): The value of the metadata key to filter by.
            table_name (Optional[str]): The name of the table to delete records from. Defaults to the instance's table name.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        table = self._open_table(table_name)
        if table is None:
            return True

        return table.delete(f"metadata.{key} = '{value}'")

    def drop(self, table_name: Optional[str] = None) -> bool:
        """
        Drops (deletes) the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to delete. Defaults to self.table_name.

        Returns:
            bool: True if the table was successfully dropped, False otherwise.
        """
        table_name = table_name or self.table_name
        table = self._open_table(table_name)
        if table is None:
            return True

        return self.client.drop_table(table_name)

    def count(self, table_name: Optional[str] = None) -> int:
        """
        Counts the number of records in the specified memory table.

        Args:
            table_name (Optional[str]): The name of the table to count records in. Defaults to self.table_name.

        Returns:
            int: The number of records in the table.
        """
        table = self._open_table(table_name)
        if table is None:
            return 0

        return table.count_rows()

    def reset(self) -> None:
        """
        Resets the memory by dropping the default memory table.
        """
        self.drop()


class Mem0:
    """
    Mem0 provides state-of-the-art retrieval and memory capabilities for
    long-term retention of prior knowledge and debugging experiences.
    """

    def __init__(self, project_path: Optional[str] = None, api_token: Optional[str] = None):
        """
        Initialize Mem0 memory.

        Args:
            project_path: optional project path, used for underlying LanceDBMemory storage
            api_token: optional Mem0 API token, if not provided uses the default community token
        """
        self.project_path = project_path or "."
        self.api_token = api_token or "community_default_token"
        self.lancedb_memory = LanceDBMemory(self.project_path)
        self.table_name = "mem0_memory"

    def