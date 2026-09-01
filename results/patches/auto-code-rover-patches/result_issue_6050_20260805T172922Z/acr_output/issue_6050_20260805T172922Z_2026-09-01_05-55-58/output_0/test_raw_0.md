```python
# reproducer.py
import time, uuid
from typing import TypedDict
from langgraph.func import task
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.constants import START, END
from langgraph.checkpoint.memory import InMemorySaver

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

# ------- helper tasks -------------------------------------------------
counter_parent = counter_sub = 0

@task
def get_time_parent() -> float:
    global counter_parent
    counter_parent += 1
    print(f"get_time_parent called {counter_parent} times")
    return time.time()

@task
def get_time_subgraph() -> float:
    global counter_sub
    counter_sub += 1
    print(f"get_time_subgraph called {counter_sub} times")
    return time.time()

# ------- sub-graph ----------------------------------------------------
class State(TypedDict):
    state_counter: int

checkpointer = InMemorySaver()

sub = StateGraph(State)
sub.add_node("some_node", lambda s: None)
def human_node(_: State):
    t1 = get_time_subgraph().result()
    print("subgraph t1:", t1)
    interrupt("what is your name?")
sub.add_node("human_node", human_node)
sub.add_edge(START, "some_node")
sub.add_edge("some_node", "human_node")
sub.add_edge("human_node", END)
subgraph = sub.compile(checkpointer=checkpointer)

# ------- parent graph -------------------------------------------------
parent = StateGraph(State)
def parent_node(_: State):
    t1 = get_time_parent().result()
    print("parent t1:", t1)
    interrupt("what is your parent name?")
parent.add_node("parent_node", parent_node)
parent.add_node("subgraph", subgraph)
parent.add_edge(START, "parent_node")
parent.add_edge("parent_node", "subgraph")
parent.add_edge("subgraph", END)
graph = parent.compile(checkpointer=checkpointer)

cfg_parent = {"configurable": {"thread_id": uuid.uuid4()}}

try:
    print('--- First run---')
    for chunk in graph.stream({"state_counter": 1}, cfg_parent):
        pass   # triggers first interrupt

    print('--- Resuming 1---')
    for chunk in graph.stream(Command(resume="resume-1"), cfg_parent):
        pass   # triggers second interrupt (inside subgraph)

    print('--- Resuming 2---')
    for chunk in graph.stream(Command(resume="resume-2"), cfg_parent):
        pass   # finishes successfully

    # Check if subgraph task re-executed
    # Expected behavior:
    #   get_time_subgraph called 1 times  => task reused cached result on resume
    # If counter_sub > 1 => bug present
    if counter_sub > 1:
        raise AssertionError(f"Subgraph task re-executed {counter_sub} times, expected 1")

except Exception as e:
    print_stacktrace(e)
    sys.exit(1)

print("Test passed, no unexpected re-executions detected.")
sys.exit(0)
```
