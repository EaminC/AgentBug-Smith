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


def main():
    import sys
    try:
        # Import project modules
        from agentscope import agentscope
        from agentscope.agents.react_agent import ReActAgent
        from agentscope.spaces import Msg
        from agentscope.toolkits.service_toolkit import ServiceToolkit
        from agentscope.toolkits.service_toolkit import execute_shell_command

        # Initialize with given model config
        agentscope.init(model_configs="./1.json")

        # Setup ServiceToolkit with execute_shell_command
        service_toolkit = ServiceToolkit()
        service_toolkit.add(execute_shell_command)

        # Instantiate agent
        agent = ReActAgent(
            name="assistant",
            model_config_name="testll",
            verbose=True,
            service_toolkit=service_toolkit,
            max_iters=1,
        )

        # Compose user message to run open calculator
        msg = Msg("user", "help me to execute the following command: open -a calculator", role="user")

        # Run agent - if exec is not isolated, this tries to open calculator
        agent(msg)

        # If no error and no isolation => bug present
        # We raise AssertionError to highlight the presence of bug
        raise AssertionError("Security bug present: arbitrary shell command executed")

    except Exception as e:
        # If error occurs, print stacktrace and exit 0 (means bug likely fixed)
        print_stacktrace(e)
        sys.exit(0)


if __name__ == "__main__":
    main()
```
