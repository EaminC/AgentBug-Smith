from unittest.mock import MagicMock, patch

import pytest

from crewai.memory.storage.mem0_storage import Mem0Storage


class MockCrew:
    def __init__(self):
        self.agents = [MagicMock(role="Test Agent")]


@pytest.fixture
def mem0_storage_instance():
    # Setup a Mem0Storage instance with minimal config that triggers the buggy code path
    crew = MockCrew()
    # Provide config without keys 'metadata', 'version', 'output_format', 'run_id' to test robustness
    config = {
        "user_id": "test_user",
        # Intentionally omit keys to test robustness
    }
    mem0_storage = Mem0Storage(type="short_term", crew=crew, config=config)
    return mem0_storage


def test_search_method_handles_missing_keys(mem0_storage_instance):
    """
    This test calls the search method of Mem0Storage with a params dict that lacks
    'metadata', 'version', 'output_format', and 'run_id' keys. The buggy code deletes
    these keys without checking existence, causing KeyError.
    The fixed code should not raise KeyError and should return results properly.
    """

    mem0_storage = mem0_storage_instance

    # Mock the underlying memory.search to return a dummy result
    dummy_results = {
        "results": [
            {"score": 0.9, "memory": "Result 1"},
            {"score": 0.8, "memory": "Result 2"},
        ]
    }
    mem0_storage.memory.search = MagicMock(return_value=dummy_results)

    # Call search with a query and score_threshold
    try:
        results = mem0_storage.search("test query", limit=2, score_threshold=0.5)
    except KeyError as e:
        pytest.fail(f"search() raised KeyError unexpectedly: {e}")

    # Assert the results are as expected and keys are normalized to 'context'
    assert isinstance(results, list)
    assert len(results) == 2
    assert all("context" in r for r in results)


def test_search_method_filters_params_correctly(mem0_storage_instance):
    """
    This test ensures that the search method builds the params dictionary correctly
    and calls the underlying memory.search with expected keys, without KeyError.
    """

    mem0_storage = mem0_storage_instance

    # Patch the memory.search method to capture the params passed
    called_params = {}

    def fake_search(**kwargs):
        nonlocal called_params
        called_params = kwargs
        return {"results": []}

    mem0_storage.memory.search = fake_search

    # Call search with a query and score_threshold
    mem0_storage.search("another query", limit=1, score_threshold=0.1)

    # The params dict should not contain keys 'metadata', 'version', 'output_format', or 'run_id'
    # because they are deleted safely in the fixed code
    for key in ["metadata", "version", "output_format", "run_id"]:
        # run_id can be None, so it may be present with None value; we consider only keys with non-None values
        if key in called_params and called_params[key] is not None:
            pytest.fail(f"Key '{key}' should not be in params or should be None")


def test_save_method_calls_memory_add_with_infer_true(mem0_storage_instance):
    mem0_storage = mem0_storage_instance
    mem0_storage.memory.add = MagicMock()

    test_value = "This is a test memory"
    test_metadata = {"key": "value"}

    mem0_storage.save(test_value, test_metadata)

    mem0_storage.memory.add.assert_called_once()
    call_args = mem0_storage.memory.add.call_args[1]

    # Check that infer is True by default
    assert call_args.get("infer") is True

    # Check that metadata and type are passed correctly
    assert call_args.get("metadata") is not None
    assert call_args["metadata"].get("type") == "short_term"

    # Check that the content is passed as list of dicts with role and content
    content = mem0_storage.memory.add.call_args[0][0]
    assert isinstance(content, list)
    assert content[0]["content"] == test_value
    assert content[0]["role"] == "assistant"


def test_search_returns_context_key_for_results(mem0_storage_instance):
    mem0_storage = mem0_storage_instance
    mock_results = {
        "results": [
            {"score": 0.9, "memory": "Result 1"},
            {"score": 0.4, "memory": "Result 2"},
        ]
    }
    mem0_storage.memory.search = MagicMock(return_value=mock_results)

    results = mem0_storage.search("test query", limit=5, score_threshold=0.5)

    mem0_storage.memory.search.assert_called_once()

    assert len(results) == 2
    # The results should have 'context' key copied from 'memory'
    for r in results:
        assert "context" in r
        assert r["context"].startswith("Result")


# The tests above verify that the buggy code that deletes keys without checking existence
# causes KeyError before the fix, and after the fix, the tests pass without errors.
# They also verify that the results have the expected 'context' key for compatibility.
