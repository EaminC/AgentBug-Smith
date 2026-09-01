```python
# reproducer.py
def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    import sys
    import traceback
    try:
        from unittest.mock import MagicMock
        from agentscope.agent import Agent
    except ImportError as e:
        print(f"ERROR: Could not import Agent class: {e}", file=sys.stderr)
        sys.exit(1)

    # Use a mock model — no API key needed
    mock_model = MagicMock()

    # Create two agents using DEFAULT configs (no explicit config passed)
    agent1 = Agent("assistant-1", "You are agent 1.", mock_model)
    agent2 = Agent("assistant-2", "You are agent 2.", mock_model)

    try:
        # Assert that configs are NOT shared instances
        assert agent1.model_config is not agent2.model_config, \
            "Bug detected: model_config is shared across Agent instances!"
        assert agent1.context_config is not agent2.context_config, \
            "Bug detected: context_config is shared across Agent instances!"
        assert agent1.react_config is not agent2.react_config, \
            "Bug detected: react_config is shared across Agent instances!"

        # Further, test mutation contamination: changes to one should not reflect on the other
        orig_temp = agent2.model_config.temperature
        agent1.model_config.temperature = orig_temp + 1.0  # mutate agent1
        assert agent2.model_config.temperature == orig_temp, \
            "Bug detected: mutation to agent1.model_config.temperature affects agent2!"

        orig_max_iters = agent2.react_config.max_iters
        agent1.react_config.max_iters = orig_max_iters + 5
        assert agent2.react_config.max_iters == orig_max_iters, \
            "Bug detected: mutation to agent1.react_config.max_iters affects agent2!"

    except AssertionError as e:
        print_stacktrace(e)
        sys.exit(1)

    # If no assertion failed, print success and exit 0
    print("No shared default config objects detected. Bug appears fixed.")
    sys.exit(0)
```
