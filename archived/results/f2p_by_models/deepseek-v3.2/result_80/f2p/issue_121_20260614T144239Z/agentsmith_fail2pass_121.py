import os
import tempfile
import shutil
import sys
import yaml
import pickle
from unittest.mock import patch, MagicMock
from mle.utils import WorkflowCache, WorkflowCacheOperator
from mle.utils.system import get_config, write_config


def test_workflow_cache_operator_store_resume():
    """Test that WorkflowCacheOperator correctly stores and resumes pickled objects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy cache instance with a mock _store_cache_buffer
        mock_cache = MagicMock()
        mock_cache._store_cache_buffer = MagicMock()
        cache_content = {}
        operator = WorkflowCacheOperator(mock_cache, cache_content)

        # Store a complex object
        test_obj = {"key": "value", "list": [1, 2, 3]}
        operator.store("test_key", test_obj)

        # Ensure the stored value is pickled bytes
        assert "test_key" in cache_content
        stored = cache_content["test_key"]
        assert isinstance(stored, bytes)
        # Verify it can be unpickled to the original object
        unpickled = pickle.loads(stored)
        assert unpickled == test_obj

        # Resume the object
        resumed = operator.resume("test_key")
        assert resumed == test_obj

        # Resume non-existent key returns None
        assert operator.resume("non_existent") is None


def test_workflow_cache_init_and_is_empty():
    """Test WorkflowCache initialization and empty check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a project.yml config file
        config_path = os.path.join(tmpdir, "project.yml")
        with open(config_path, "w") as f:
            yaml.dump({"other": "value"}, f)

        # Change to the temp directory so get_config finds the file
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            cache = WorkflowCache(tmpdir)
            # Initially cache should be empty because config has no "cache" key
            assert cache.is_empty()
            assert cache.cache == {}

            # Now write a config with cache content
            with open(config_path, "w") as f:
                yaml.dump({"cache": {1: {"step": 1, "name": "test", "time": "2024-01-01", "content": {}}}}, f)
            # Re-initialize (but note: WorkflowCache loads config at init, so we need a new instance)
            cache2 = WorkflowCache(tmpdir)
            assert not cache2.is_empty()
            assert cache2.cache[1]["name"] == "test"
        finally:
            os.chdir(original_cwd)


def test_workflow_cache_call_creates_step():
    """Test that calling cache with a step creates a new step entry if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        with open(config_path, "w") as f:
            yaml.dump({}, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            cache = WorkflowCache(tmpdir)
            assert cache.is_empty()

            # Call with step 1
            operator = cache(step=1, name="first_step")
            assert isinstance(operator, WorkflowCacheOperator)
            assert 1 in cache.cache
            assert cache.cache[1]["name"] == "first_step"
            assert "time" in cache.cache[1]
            assert cache.cache[1]["content"] == {}

            # Call again with same step should not overwrite name/time
            original_time = cache.cache[1]["time"]
            operator2 = cache(step=1, name="different_name")
            assert cache.cache[1]["name"] == "first_step"  # unchanged
            assert cache.cache[1]["time"] == original_time  # unchanged
        finally:
            os.chdir(original_cwd)


def test_workflow_cache_remove():
    """Test removing a step from cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        with open(config_path, "w") as f:
            yaml.dump({"cache": {1: {"step": 1, "name": "step1", "time": "2024-01-01", "content": {}},
                                 2: {"step": 2, "name": "step2", "time": "2024-01-02", "content": {}}}}, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            cache = WorkflowCache(tmpdir)
            assert 1 in cache.cache
            assert 2 in cache.cache

            # Mock the _store_cache_buffer to verify it's called
            original_store = cache._store_cache_buffer
            call_count = 0
            def mock_store():
                nonlocal call_count
                call_count += 1
                original_store()
            cache._store_cache_buffer = mock_store

            cache.remove(1)
            assert 1 not in cache.cache
            assert 2 in cache.cache
            assert call_count == 1

            # Removing non-existent step does nothing
            cache.remove(99)
            assert call_count == 2  # still called because remove always calls _store_cache_buffer
        finally:
            os.chdir(original_cwd)


def test_workflow_cache_current_step():
    """Test current_step returns max key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        with open(config_path, "w") as f:
            yaml.dump({"cache": {5: {"step": 5, "name": "five", "time": "2024-01-05", "content": {}},
                                 3: {"step": 3, "name": "three", "time": "2024-01-03", "content": {}}}}, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            cache = WorkflowCache(tmpdir)
            assert cache.current_step() == 5

            # Empty cache: max of empty keys should raise ValueError? Actually max([]) raises ValueError.
            # But the code uses max(self.cache.keys()) which will raise ValueError if cache is empty.
            # However, the baseline workflow checks is_empty before calling current_step.
            # We'll test that edge case.
            cache.cache = {}
            try:
                cache.current_step()
                assert False, "Expected ValueError for empty cache"
            except ValueError:
                pass  # expected
        finally:
            os.chdir(original_cwd)


def test_workflow_cache_operator_context_manager():
    """Test that the context manager calls _store_cache_buffer on exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        with open(config_path, "w") as f:
            yaml.dump({}, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            cache = WorkflowCache(tmpdir)
            cache._store_cache_buffer = MagicMock()

            with cache(step=10, name="context_step") as op:
                op.store("data", "value")
                # Ensure store works inside context
                assert "data" in cache.cache[10]["content"]

            # After exiting context, _store_cache_buffer should be called
            cache._store_cache_buffer.assert_called_once()

            # If an exception occurs, _store_cache_buffer should NOT be called (only when exc_type is None)
            cache._store_cache_buffer.reset_mock()
            try:
                with cache(step=11, name="exception_step") as op:
                    raise RuntimeError("test exception")
            except RuntimeError:
                pass
            cache._store_cache_buffer.assert_not_called()
        finally:
            os.chdir(original_cwd)


def test_write_config():
    """Test that write_config writes to project.yml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            data = {"cache": {1: {"step": 1}}, "other": "value"}
            write_config(data)
            config_path = os.path.join(tmpdir, "project.yml")
            assert os.path.exists(config_path)
            with open(config_path, "r") as f:
                loaded = yaml.safe_load(f)
            assert loaded == data
        finally:
            os.chdir(original_cwd)


def test_baseline_workflow_resume_logic():
    """Test the resume logic in baseline workflow using cache."""
    # This test mocks the user inputs and agents to simulate a resume scenario.
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        # Simulate a cache with step 1 already stored
        cache_data = {
            "cache": {
                1: {
                    "step": 1,
                    "name": "ask for the data information",
                    "time": "2024-01-01",
                    "content": {"dataset": pickle.dumps("cached_dataset", fix_imports=False)}
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(cache_data, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Mock ask_text to return empty (simulating user pressing ENTER)
            with patch('mle.utils.ask_text') as mock_ask:
                mock_ask.return_value = ""  # ENTER -> no step picked
                cache = WorkflowCache(tmpdir)
                assert not cache.is_empty()
                # The cache should have the stored dataset
                with cache(step=1, name="ask for the data information") as ca:
                    dataset = ca.resume("dataset")
                    assert dataset == "cached_dataset"
                    # If we store something new, it should be pickled
                    ca.store("new", [1,2,3])
                    assert "new" in cache.cache[1]["content"]
                    assert isinstance(cache.cache[1]["content"]["new"], bytes)
        finally:
            os.chdir(original_cwd)


def test_baseline_workflow_resume_with_step_selection():
    """Test that selecting a step for resume removes stale steps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "project.yml")
        cache_data = {
            "cache": {
                1: {"step": 1, "name": "step1", "time": "2024-01-01", "content": {}},
                2: {"step": 2, "name": "step2", "time": "2024-01-02", "content": {}},
                3: {"step": 3, "name": "step3", "time": "2024-01-03", "content": {}}
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(cache_data, f)

        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Mock ask_text to return "2" (resume from step 2)
            with patch('mle.utils.ask_text') as mock_ask:
                mock_ask.return_value = "2"
                cache = WorkflowCache(tmpdir)
                # Simulate the logic from baseline: if step is given, remove steps >= step
                step = mock_ask.return_value
                if step:
                    step = int(step)
                    for i in range(step, cache.current_step() + 1):
                        cache.remove(i)
                # After removal, step 2 and 3 should be gone, step 1 remains
                assert 1 in cache.cache
                assert 2 not in cache.cache
                assert 3 not in cache.cache
        finally:
            os.chdir(original_cwd)
