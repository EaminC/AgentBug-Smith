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


import sys
import asyncio
from typing import Dict, List
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.version import __version__ as version


class State(TypedDict):
    foo: str


async def call_model(state: State, config: dict) -> Dict[str, List[AIMessage]]:
    print("CONFIG", config)
    return {"foo": "bar"}


async def main():
    builder = StateGraph(State)
    builder.add_node(call_model)
    builder.add_edge("__start__", "call_model")
    graph = builder.compile(name="ReAct Agent")

    async for _ in graph.astream(
        {
            "messages": [{"role": "user", "content": "Hi there!"}],
            "configurable": {"foo": "bar"},
        }
    ):
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
        print(f"Passed in langgraph version=={version}")
        # if no error, exit 0 meaning issue is fixed
        sys.exit(0)
    except Exception as e:
        print(f"Failed in langgraph version=={version}")
        print("ERROR", e)
        print_stacktrace(e)
        # Raise AssertionError so CI detecting failure of issue reproduction
        raise AssertionError(
            "Detected the config typing issue: should raise helpful warning for `config: dict`"
        ) from e
```
