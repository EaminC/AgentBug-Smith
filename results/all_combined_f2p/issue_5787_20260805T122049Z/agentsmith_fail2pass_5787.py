from __future__ import annotations

import warnings
from typing import Any, Optional

import pytest
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph
from langgraph.warnings import LangGraphDeprecatedSinceV05, LangGraphDeprecatedSinceV10
from typing_extensions import TypedDict


class PlainState(TypedDict):
    pass


def test_config_parameter_incorrect_typing() -> None:
    """Test that a warning is raised when config parameter is typed incorrectly."""
    builder = StateGraph(PlainState)

    # Test sync function with config: dict
    with pytest.warns(
        UserWarning,
        match="The 'config' parameter should be typed as 'RunnableConfig' or 'RunnableConfig | None', not '.*dict.*'. ",
    ):

        def sync_node_with_dict_config(state: PlainState, config: dict) -> PlainState:
            return state

        builder.add_node(sync_node_with_dict_config)

    # Test async function with config: dict
    with pytest.warns(
        UserWarning,
        match="The 'config' parameter should be typed as 'RunnableConfig' or 'RunnableConfig | None', not '.*dict.*'. ",
    ):

        async def async_node_with_dict_config(
            state: PlainState, config: dict
        ) -> PlainState:
            return state

        builder.add_node(async_node_with_dict_config)

    # Test with other incorrect types
    with pytest.warns(
        UserWarning,
        match="The 'config' parameter should be typed as 'RunnableConfig' or 'RunnableConfig | None', not '.*Any.*'. ",
    ):

        def sync_node_with_any_config(state: PlainState, config: Any) -> PlainState:
            return state

        builder.add_node(sync_node_with_any_config)

    with pytest.warns(
        UserWarning,
        match="The 'config' parameter should be typed as 'RunnableConfig' or 'RunnableConfig | None', not '.*Any.*'. ",
    ):

        async def async_node_with_any_config(
            state: PlainState, config: Any
        ) -> PlainState:
            return state

        builder.add_node(async_node_with_any_config)

    with warnings.catch_warnings(record=True) as w:

        def node_with_correct_config(
            state: PlainState, config: RunnableConfig
        ) -> PlainState:
            return state

        builder.add_node(node_with_correct_config)

        def node_with_optional_config(
            state: PlainState,
            config: Optional[RunnableConfig],  # noqa: UP045
        ) -> PlainState:
            return state

        builder.add_node(node_with_optional_config)

        def node_with_untyped_config(state: PlainState, config) -> PlainState:
            return state

        builder.add_node(node_with_untyped_config)

        async def async_node_with_correct_config(
            state: PlainState, config: RunnableConfig
        ) -> PlainState:
            return state

        builder.add_node(async_node_with_correct_config)

        async def async_node_with_optional_config(
            state: PlainState,
            config: Optional[RunnableConfig],  # noqa: UP045
        ) -> PlainState:
            return state

        builder.add_node(async_node_with_optional_config)

        async def async_node_with_untyped_config(
            state: PlainState, config
        ) -> PlainState:
            return state

        builder.add_node(async_node_with_untyped_config)
        assert len(w) == 0
