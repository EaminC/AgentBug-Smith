```python
# reproducer.py
from dataclasses import dataclass
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph
from langgraph.runtime import Runtime


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


@dataclass
class Context:
    username: str


class State(TypedDict):
    foo: str


def subgraph_node_1(state: State, runtime: Runtime[Context]):
    # This will raise AttributeError if runtime.context is None
    return {'foo': 'hi! ' + runtime.context.username}


def main_node(state: State, runtime: Runtime[Context]):
    return {'foo': 'hello ' + runtime.context.username}


import sys

def main():
    # Build subgraph
    subgraph_builder = StateGraph(State, context_schema=Context)
    subgraph_builder.add_node(subgraph_node_1)
    subgraph_builder.set_entry_point('subgraph_node_1')
    subgraph = subgraph_builder.compile()

    # Build parent graph
    builder = StateGraph(State, context_schema=Context)
    builder.add_node(main_node)
    builder.add_node('node_1', subgraph)
    builder.set_entry_point('main_node')
    builder.add_edge('main_node', 'node_1')
    graph = builder.compile()

    context = Context(username='Alice')
    try:
        # This should run without error if the runtime context is propagated correctly
        result = graph.invoke({'foo': 'world'}, context=context)
        assert 'hi! Alice' in result['foo'] or 'hello Alice' in result['foo'], \
            "Runtime context username not found in output"
    except Exception as e:
        # Print the stacktrace in the requested format
        print_stacktrace(e)
        # Raise AssertionError to indicate the issue is present
        raise AssertionError("Runtime context is not propagated to the subgraph") from e


if __name__ == "__main__":
    main()
```
