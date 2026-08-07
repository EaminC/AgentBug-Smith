import pytest
from typing import TypedDict

from langgraph.graph import StateGraph


def test_invalid_checkpointer_type() -> None:
    """Test that an invalid checkpointer type raises a TypeError with a helpful message."""
    class State(TypedDict):
        foo: str

    builder = StateGraph(State)
    builder.add_node("start", lambda state: state)
    builder.set_entry_point("start")
    builder.set_finish_point("start")

    class NotACheckpointer:
        pass

    with pytest.raises(TypeError, match="Invalid checkpointer provided"):
        builder.compile(checkpointer=NotACheckpointer())
