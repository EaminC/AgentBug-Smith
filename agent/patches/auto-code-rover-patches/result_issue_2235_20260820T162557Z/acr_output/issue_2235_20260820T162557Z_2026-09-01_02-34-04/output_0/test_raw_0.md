```python
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
    try:
        from strands import Agent
        from strands.models.ollama import OllamaModel
    except ImportError as e:
        print("Error: Failed to import required modules. Are you running this inside the project environment?", file=sys.stderr)
        print_stacktrace(e)
        sys.exit(1)

    # Create an Ollama model instance
    ollama_model = OllamaModel(
        host="http://localhost:11434",
        model_id="gpt-oss",
    )

    # Create an agent using the Ollama model
    agent = Agent(
        model=ollama_model,
    )

    try:
        # Use the agent
        result = agent("Tell me about Strands agents in 2 lines")

        # Extract accumulated_metrics
        accumulated_metrics = result.metrics.get_summary()["accumulated_metrics"]

        latency_ms = accumulated_metrics.get("latencyMs")
        # Check if latencyMs is int as required
        assert isinstance(latency_ms, int), f"latencyMs is not int: {latency_ms} (type={type(latency_ms)})"

    except AssertionError as e:
        print_stacktrace(e)
        # The bug is present so exit code is non-zero
        sys.exit(1)
    except Exception as e:
        # print any other unexpected error
        print_stacktrace(e)
        sys.exit(1)
    else:
        # No assertion error, bug fixed
        print("latencyMs is int as expected. Issue resolved.")
        sys.exit(0)
```
