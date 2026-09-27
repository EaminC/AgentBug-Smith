import importlib
import sys
import warnings
from unittest.mock import Mock

import pytest

from strands.experimental.hooks import (
    AfterModelInvocationEvent,
    AfterToolInvocationEvent,
    BeforeModelInvocationEvent,
    BeforeToolInvocationEvent,
)
from strands.hooks import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    BeforeToolCallEvent,
    HookRegistry,
)


def test_experimental_aliases_are_same_types():
    """Verify that experimental aliases are identical to the actual types."""
    assert BeforeToolInvocationEvent is BeforeToolCallEvent
    assert AfterToolInvocationEvent is AfterToolCallEvent
    assert BeforeModelInvocationEvent is BeforeModelCallEvent
    assert AfterModelInvocationEvent is AfterModelCallEvent

    assert BeforeToolCallEvent is BeforeToolInvocationEvent
    assert AfterToolCallEvent is AfterToolInvocationEvent
    assert BeforeModelCallEvent is BeforeModelInvocationEvent
    assert AfterModelCallEvent is AfterModelInvocationEvent


def test_before_tool_call_event_type_equality():
    """Verify that BeforeToolInvocationEvent alias has the same type identity."""
    before_tool_event = BeforeToolCallEvent(
        agent=Mock(),
        selected_tool=Mock(),
        tool_use={"name": "test", "toolUseId": "123", "input": {}},
        invocation_state={},
    )

    assert isinstance(before_tool_event, BeforeToolInvocationEvent)
    assert isinstance(before_tool_event, BeforeToolCallEvent)


def test_after_tool_call_event_type_equality():
    """Verify that AfterToolInvocationEvent alias has the same type identity."""
    after_tool_event = AfterToolCallEvent(
        agent=Mock(),
        selected_tool=Mock(),
        tool_use={"name": "test", "toolUseId": "123", "input": {}},
        invocation_state={},
        result={"toolUseId": "123", "status": "success", "content": [{"text": "result"}]},
    )

    assert isinstance(after_tool_event, AfterToolInvocationEvent)
    assert isinstance(after_tool_event, AfterToolCallEvent)


def test_before_model_call_event_type_equality():
    """Verify that BeforeModelInvocationEvent alias has the same type identity."""
    before_model_event = BeforeModelCallEvent(agent=Mock())

    assert isinstance(before_model_event, BeforeModelInvocationEvent)
    assert isinstance(before_model_event, BeforeModelCallEvent)


def test_after_model_call_event_type_equality():
    """Verify that AfterModelInvocationEvent alias has the same type identity."""
    after_model_event = AfterModelCallEvent(agent=Mock())

    assert isinstance(after_model_event, AfterModelInvocationEvent)
    assert isinstance(after_model_event, AfterModelCallEvent)


def test_experimental_aliases_in_hook_registry():
    """Verify that experimental aliases work with hook registry callbacks."""
    hook_registry = HookRegistry()
    callback_called = False
    received_event = None

    def experimental_callback(event: BeforeToolInvocationEvent):
        nonlocal callback_called, received_event
        callback_called = True
        received_event = event

    # Register callback using experimental alias
    hook_registry.add_callback(BeforeToolInvocationEvent, experimental_callback)

    # Create event using actual type
    test_event = BeforeToolCallEvent(
        agent=Mock(),
        selected_tool=Mock(),
        tool_use={"name": "test", "toolUseId": "123", "input": {}},
        invocation_state={},
    )

    # Invoke callbacks - should work since alias points to same type
    hook_registry.invoke_callbacks(test_event)

    assert callback_called
    assert received_event is test_event


def test_deprecation_warning_on_import():
    """Verify that importing from experimental module emits deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # Import the experimental hooks events module to trigger warning
        if "strands.experimental.hooks.events" in sys.modules:
            importlib.reload(sys.modules["strands.experimental.hooks.events"])
        else:
            importlib.import_module("strands.experimental.hooks.events")

        assert any(
            issubclass(warn.category, DeprecationWarning)
            and "moved to production with updated names" in str(warn.message)
            for warn in w
        )


def test_no_deprecation_warning_on_hooks_import():
    """Verify that importing from strands.hooks does not emit deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        if "strands.hooks" in sys.modules:
            importlib.reload(sys.modules["strands.hooks"])
        else:
            importlib.import_module("strands.hooks")

        # There should be no DeprecationWarning when importing from strands.hooks
        assert not any(issubclass(warn.category, DeprecationWarning) for warn in w)
