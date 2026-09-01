```python
# reproducer.py
import threading
import time
import sys

def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


def reproducer():
    """
    Reproduce the bug where AfterNodeCallEvent is emitted even if a node is interrupted.
    We listen for AfterNodeCallEvent during a node call in multi-agent execution,
    interrupt it, and check if the event was emitted or not.
    """

    from strands.core.events import AfterNodeCallEvent
    from strands.core.actors.graph import Graph
    from strands.core.actors.swarm import Swarm
    from strands.core.environment import Environment
    from strands.tools.executors._executor import ToolExecutor

    # Flags to monitor event calls
    after_node_call_emitted = False

    # Event handler for AfterNodeCallEvent
    def after_node_call_handler(event):
        nonlocal after_node_call_emitted
        after_node_call_emitted = True

    # Build a minimal environment and graph with a node that sleeps sufficiently long to interrupt
    env = Environment()

    # We create a graph with a single node that sleeps for some time.
    # Implementation detail: name of the node must be unique.
    graph = Graph(name="test_graph", environment=env)

    @graph.node
    def sleeper_node(*args, **kwargs):
        # Sleep longer than the interrupt wait to guarantee interrupt can occur
        time.sleep(2)
        return "done"

    # Attach event listener
    env.event_bus.on(AfterNodeCallEvent, after_node_call_handler)

    # We run the graph in a separate thread to allow interrupt
    def run_graph():
        graph.run()

    t = threading.Thread(target=run_graph)
    t.start()

    # Sleep shortly, then send interrupt signal to the environment/process
    time.sleep(0.3)
    # Interrupt the graph run - simulate an interrupt signal
    env.interrupt()

    # Wait for thread to finish
    t.join(timeout=5)

    # Assertion:
    # As per issue, AfterNodeCallEvent should NOT emit if node is interrupted.
    # So after_node_call_emitted must be False.
    try:
        assert not after_node_call_emitted, "AfterNodeCallEvent was emitted despite node interrupt!"
    except AssertionError as e:
        print_stacktrace(e)
        sys.exit(1)


if __name__ == "__main__":
    reproducer()
    print("No AfterNodeCallEvent emitted on node interrupt: bug fixed.")
    sys.exit(0)
```
