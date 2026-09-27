import time
import uuid
from typing import TypedDict

from langgraph.func import task
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.constants import START, END
from langgraph.checkpoint.memory import InMemorySaver


def test_nested_graph_resume_reuses_cached_task_writes() -> None:
    # Reproduces issue where a helper @task inside a nested graph re-executes
    # on resume instead of reusing cached writes. Ensures it runs only once.
    counter_parent = 0
    counter_sub = 0

    @task
    def get_time_parent() -> float:
        nonlocal counter_parent
        counter_parent += 1
        return time.time()

    @task
    def get_time_subgraph() -> float:
        nonlocal counter_sub
        counter_sub += 1
        return time.time()

    class State(TypedDict):
        state_counter: int

    # Subgraph that calls a helper task and then interrupts
    sub = StateGraph(State)

    def human_node(_: State):
        _ = get_time_subgraph().result()
        interrupt("what is your name?")

    sub.add_node("human_node", human_node)
    sub.set_entry_point("human_node")
    sub.set_finish_point("human_node")
    subgraph = sub.compile(checkpointer=InMemorySaver())

    # Parent graph that calls a helper task and interrupts, then enters subgraph
    parent = StateGraph(State)

    def parent_node(_: State):
        _ = get_time_parent().result()
        interrupt("what is your parent name?")

    parent.add_node("parent_node", parent_node)
    parent.add_node("subgraph", subgraph)
    parent.add_edge(START, "parent_node")
    parent.add_edge("parent_node", "subgraph")
    parent.add_edge("subgraph", END)
    graph = parent.compile(checkpointer=InMemorySaver())

    cfg_parent = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # First run – interrupts in parent node
    for _ in graph.stream({"state_counter": 1}, cfg_parent):
        pass

    # Resume 1 – proceeds into subgraph, interrupts there
    for _ in graph.stream(Command(resume="resume-1"), cfg_parent):
        pass

    # Resume 2 – completes without re-running subgraph helper task
    for _ in graph.stream(Command(resume="resume-2"), cfg_parent):
        pass

    assert counter_parent == 1
    assert counter_sub == 1
