import os
import builtins
import pytest
from unittest import mock

# We will test the new WorkflowCache and baseline workflow resume behavior
# introduced by the patch for issue 121.
# The tests will fail on buggy code (no WorkflowCache class, no resume logic),
# and pass after the fix is applied.

def test_baseline_resume_flow_and_caching(tmp_path, monkeypatch):
    """
    Test that baseline.py workflow can resume from previous steps using WorkflowCache.
    This test mocks user input and model interactions to simulate a partial workflow,
    then restarts and resumes from a cached step.
    """
    import mle.workflow.baseline as baseline_mod
    from mle.utils.cache import WorkflowCache

    # Prepare a dummy project directory
    project_dir = tmp_path
    # Create a dummy project.yml to avoid None from get_config()
    config_path = project_dir / "project.yml"
    config_path.write_text("cache: {}\n")

    # Patch get_config and write_config to read/write from project.yml in tmp_path
    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    # Patch ask_text to simulate user input for dataset and requirement
    # We simulate first run: user inputs dataset and requirement
    # Then second run: user inputs step to resume and no new inputs for dataset/requirement
    inputs = iter([
        "my_dataset",        # dataset input for step 1
        "my_requirement",    # requirement input for step 2
        "",                  # step to resume (empty = continue)
    ])
    def fake_ask_text(prompt):
        return next(inputs)

    monkeypatch.setattr("mle.utils.interaction.ask_text", fake_ask_text)

    # Patch questionary.confirm to always return False (no debug)
    monkeypatch.setattr("questionary.confirm", lambda *a, **kw: mock.Mock(ask=lambda: False)())

    # Patch model loading to return a dummy model object using environment variable
    monkeypatch.setattr("mle.model.load_model", lambda work_dir, model: os.getenv("OPENAI_API_KEY", "dummy_model"))

    # Patch agents to simulate interact calls returning canned responses
    class DummyAgent:
        def __init__(self, *args, **kwargs):
            pass
        def interact(self, prompt):
            if "User Requirement" in prompt:
                return "advisor_report"
            return "plan_report"
        def read_requirement(self, report):
            pass
        def debug(self, task, debug_report):
            return {"debug": "False"}
        def analyze(self, code_report):
            return {"status": "success"}

    monkeypatch.setattr("mle.agents.AdviseAgent", lambda model, console: DummyAgent())
    monkeypatch.setattr("mle.agents.PlanAgent", lambda model, console: DummyAgent())
    monkeypatch.setattr("mle.agents.CodeAgent", lambda model, work_dir, console: DummyAgent())
    monkeypatch.setattr("mle.agents.DebugAgent", lambda model, console: DummyAgent())

    # Patch console to dummy object with status context manager
    class DummyConsole:
        def status(self, msg):
            class DummyStatus:
                def __enter__(self_): return self_
                def __exit__(self_, exc_type, exc_val, exc_tb): return False
            return DummyStatus()
    monkeypatch.setattr("rich.console.Console", DummyConsole)

    # Run baseline first time to create cache
    baseline_mod.baseline(str(project_dir), model=os.getenv("OPENAI_API_KEY", "dummy_model"))

    # Now simulate a restart: user inputs step to resume as 1, so steps 1..current_step removed
    inputs2 = iter([
        "1",  # resume from step 1
        # no inputs for dataset or requirement because they should be resumed
    ])
    monkeypatch.setattr("mle.utils.interaction.ask_text", lambda prompt: next(inputs2))

    # Run baseline again, should resume and not ask dataset/requirement again
    baseline_mod.baseline(str(project_dir), model=os.getenv("OPENAI_API_KEY", "dummy_model"))

    # Check that cache file exists and contains expected keys
    cache = WorkflowCache(str(project_dir))
    assert not cache.is_empty()
    # The cache should contain step 1..5 keys after full run
    for step in range(1, 6):
        assert step in cache.cache

def test_workflow_cache_operator_store_and_resume(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache

    # Prepare dummy config file to avoid None from get_config
    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    with cache(1, "test") as op:
        op.store("key1", "value1")
        resumed = op.resume("key1")
        assert resumed == "value1"
        # Resume non-existent key returns None
        assert op.resume("nokey") is None

def test_workflow_cache_str_and_empty_behavior(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    assert cache.is_empty()
    s = str(cache)
    assert isinstance(s, str)
    # Add a step and check not empty
    with cache(1, "name1"):
        pass
    assert not cache.is_empty()
    s2 = str(cache)
    assert "[1]" in s2

def test_workflow_cache_remove_and_current_step(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    with cache(1, "step1"):
        pass
    with cache(2, "step2"):
        pass
    assert cache.current_step() == 2
    cache.remove(2)
    assert 2 not in cache.cache
    assert cache.current_step() == 1

def test_workflow_cache_operator_context_manager_calls_store_cache_buffer(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache, WorkflowCacheOperator

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    called = {}
    def fake_write_config(value):
        called["called"] = True

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    op = WorkflowCacheOperator(cache, {})
    with op:
        op.store("k", "v")
    assert called.get("called") is True

def test_workflow_cache_operator_context_manager_does_not_store_on_exception(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache, WorkflowCacheOperator

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    called = {}
    def fake_write_config(value):
        called["called"] = True

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    op = WorkflowCacheOperator(cache, {})
    with pytest.raises(ValueError):
        with op:
            op.store("k", "v")
            raise ValueError("fail")
    assert called.get("called") is None

def test_workflow_cache_operator_pickle_complex_object(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    complex_obj = {"a": [1, 2, 3], "b": {"x": 10}}
    with cache(1, "test") as op:
        op.store("complex", complex_obj)
        resumed = op.resume("complex")
        assert resumed == complex_obj

@pytest.mark.parametrize("step,name", [(1, "test1"), (2, "test2")])
def test_workflow_cache_call_creates_steps(tmp_path, step, name, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    with cache(step, name) as op:
        op.store("data", step)
    assert step in cache.cache
    assert cache.cache[step]["name"] == name

def test_workflow_cache_load_cache_buffer_none(tmp_path, monkeypatch):
    import mle.utils.cache as cache_mod

    config_path = tmp_path / "project.yml"
    # Write empty file to simulate empty config
    config_path.write_text("")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            try:
                return yaml.safe_load(f)
            except Exception:
                return {}
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = cache_mod.WorkflowCache(str(tmp_path))
    # Should not raise and cache dict should exist
    assert isinstance(cache.cache, dict)

def test_workflow_cache_remove_nonexistent_key(tmp_path, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    # Removing nonexistent key should not raise
    cache.remove(999)

@pytest.mark.parametrize("step,name", [(1, "test1"), (2, "test2")])
def test_workflow_cache_operator_store_overwrite(tmp_path, step, name, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    with cache(step, name) as op:
        op.store("key", "value1")
        op.store("key", "value2")
        resumed = op.resume("key")
        assert resumed == "value2"

@pytest.mark.parametrize("step,name", [(1, "test1"), (2, "test2")])
def test_workflow_cache_operator_resume_none(tmp_path, step, name, monkeypatch):
    from mle.utils.cache import WorkflowCache

    config_path = tmp_path / "project.yml"
    config_path.write_text("cache: {}\n")

    def fake_get_config():
        import yaml
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    def fake_write_config(value):
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(value, f, default_flow_style=False)

    monkeypatch.setattr("mle.utils.system.get_config", fake_get_config)
    monkeypatch.setattr("mle.utils.system.write_config", fake_write_config)

    cache = WorkflowCache(str(tmp_path))
    with cache(step, name) as op:
        assert op.resume("nonexistent") is None