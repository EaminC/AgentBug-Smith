```python
# reproducer.py
import inspect
import sys
import typing
from typing import Callable, TypeVar, Union, get_origin, get_type_hints, List


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


# === Simulated Base classes and types ===
class BaseHookEvent:
    pass


class BeforeModelCallEvent(BaseHookEvent):
    pass


class AfterModelCallEvent(BaseHookEvent):
    pass


class NotAnEvent:
    pass


TEvent = TypeVar('TEvent', bound=BaseHookEvent)
HookCallback = Callable[[TEvent], None]


# === Simplified registry mimicking the reported behavior ===
class HookRegistry:
    def __init__(self):
        # map event type to list of callbacks
        self._callbacks: dict[type[BaseHookEvent], List[HookCallback]] = {}

    def _infer_event_types(self, callback: HookCallback[TEvent]) -> list[type[TEvent]]:
        """
        Extract all event types from callback's type hint, handling unions.
        Raise ValueError on None/Optional in union or invalid event types.
        """
        hints = get_type_hints(callback)
        sig = inspect.signature(callback)
        params = list(sig.parameters.values())

        if len(params) == 0:
            raise ValueError("Callback must have at least one parameter")

        first_param_name = params[0].name
        type_hint = hints.get(first_param_name)
        if type_hint is None:
            raise ValueError("First parameter of callback must be type-annotated")

        origin = get_origin(type_hint)

        if origin is Union:
            # Check for nested unions not supported
            args = get_args(type_hint)
            if any(get_origin(a) is Union for a in args):
                raise ValueError("Nested unions in callback parameter type are not supported")

            event_types: list[type[TEvent]] = []
            for arg in args:
                if arg is type(None):
                    raise ValueError("None/Optional type in union is not allowed")
                if not (isinstance(arg, type) and issubclass(arg, BaseHookEvent)):
                    raise ValueError(f"Invalid type in union: {arg}")
                event_types.append(arg)
            return event_types

        # Not a union: must be a subtype of BaseHookEvent
        if not (isinstance(type_hint, type) and issubclass(type_hint, BaseHookEvent)):
            raise ValueError(f"Invalid callback parameter type: {type_hint}")

        return [type_hint]

    def add_callback(self, callback: HookCallback[TEvent], event_types: type[TEvent] | list[type[TEvent]] | None = None) -> None:
        """
        Add callback to one or more event types.
        If event_types is None, infer from callback annotation.
        """
        if event_types is None:
            event_types_list = self._infer_event_types(callback)
        else:
            # if a single type is passed, convert to list
            if isinstance(event_types, list):
                event_types_list = event_types
            else:
                event_types_list = [event_types]

            # Deduplicate event types
            event_types_list = list(dict.fromkeys(event_types_list))
            # Validate all are subclasses of BaseHookEvent
            for et in event_types_list:
                if not (isinstance(et, type) and issubclass(et, BaseHookEvent)):
                    raise ValueError(f"Invalid event type in list: {et}")

        # Register callback for each event type
        for et in event_types_list:
            if et not in self._callbacks:
                self._callbacks[et] = []
            if callback not in self._callbacks[et]:
                self._callbacks[et].append(callback)


# === Agent holding the registry and providing add_hook ===
class Agent:
    def __init__(self):
        self._registry = HookRegistry()

    def add_hook(self, callback: HookCallback[TEvent], event_type: type[TEvent] | list[type[TEvent]] | None = None) -> None:
        """
        Register a callback for one or more event types.

        Accepts:
        - event_type as None to infer from callback's first parameter type hint (including unions).
        - event_type as single type or list of types.
        """
        self._registry.add_callback(callback, event_type)


# === Test functions for validations ===

agent = Agent()

def test_union_type_registration():
    # Callback with union type: BeforeModelCallEvent | AfterModelCallEvent
    def hook(event: BeforeModelCallEvent | AfterModelCallEvent) -> None:
        pass

    agent.add_hook(hook)
    registry = agent._registry._callbacks

    # Both event types must be keys in the registry with hook registered
    assert BeforeModelCallEvent in registry, "BeforeModelCallEvent not registered"
    assert AfterModelCallEvent in registry, "AfterModelCallEvent not registered"
    assert hook in registry[BeforeModelCallEvent], "Hook missing in BeforeModelCallEvent"
    assert hook in registry[AfterModelCallEvent], "Hook missing in AfterModelCallEvent"


def test_union_type_using_typing_union():
    from typing import Union as TypingUnion

    def hook(event: TypingUnion[BeforeModelCallEvent, AfterModelCallEvent]) -> None:
        pass

    agent.add_hook(hook)
    registry = agent._registry._callbacks

    # Both event types must be keys in the registry with hook registered
    assert BeforeModelCallEvent in registry, "BeforeModelCallEvent not registered (typing.Union)"
    assert AfterModelCallEvent in registry, "AfterModelCallEvent not registered (typing.Union)"
    assert hook in registry[BeforeModelCallEvent], "Hook missing in BeforeModelCallEvent (typing.Union)"
    assert hook in registry[AfterModelCallEvent], "Hook missing in AfterModelCallEvent (typing.Union)"


def test_none_in_union_raises():
    try:
        def hook(event: BeforeModelCallEvent | None) -> None:
            pass
        agent.add_hook(hook)
    except ValueError as e:
        assert "None/Optional type in union is not allowed" in str(e)
    else:
        raise AssertionError("Expected ValueError for None in union but got none")


def test_optional_in_union_raises():
    from typing import Optional

    try:
        def hook(event: Optional[BeforeModelCallEvent]) -> None:
            pass
        agent.add_hook(hook)
    except ValueError as e:
        assert "None/Optional type in union is not allowed" in str(e)
    else:
        raise AssertionError("Expected ValueError for Optional in union but got none")


def test_non_basehookevent_in_union_raises():
    try:
        def hook(event: BeforeModelCallEvent | NotAnEvent) -> None:
            pass
        agent.add_hook(hook)
    except ValueError as e:
        assert "Invalid type in union" in str(e)
    else:
        raise AssertionError("Expected ValueError for invalid non-BaseHookEvent in union but got none")


def test_add_hook_with_list_of_types():
    def hook(event) -> None:
        pass

    agent.add_hook(hook, [BeforeModelCallEvent, AfterModelCallEvent])

    registry = agent._registry._callbacks
    assert BeforeModelCallEvent in registry, "BeforeModelCallEvent not registered with list input"
    assert AfterModelCallEvent in registry, "AfterModelCallEvent not registered with list input"
    assert hook in registry[BeforeModelCallEvent]
    assert hook in registry[AfterModelCallEvent]


def test_add_hook_with_list_duplicates():
    def hook(event) -> None:
        pass

    # Add same hook with duplicated event types in list
    agent.add_hook(hook, [BeforeModelCallEvent, BeforeModelCallEvent, AfterModelCallEvent])
    registry = agent._registry._callbacks

    # Check that hook registered once per event type
    assert registry[BeforeModelCallEvent].count(hook) == 1, "Duplicate registration for BeforeModelCallEvent"
    assert registry[AfterModelCallEvent].count(hook) == 1, "Duplicate registration for AfterModelCallEvent"


def test_add_hook_removes_kwargs():
    # Here, we check that add_hook() does not have **kwargs anymore.
    sig = inspect.signature(agent.add_hook)
    params = list(sig.parameters.values())
    for param in params:
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            raise AssertionError("add_hook should not accept **kwargs")


# Run tests and catch AssertionError to print stacktrace
if __name__ == "__main__":
    tests = [
        test_union_type_registration,
        test_union_type_using_typing_union,
        test_none_in_union_raises,
        test_optional_in_union_raises,
        test_non_basehookevent_in_union_raises,
        test_add_hook_with_list_of_types,
        test_add_hook_with_list_duplicates,
        test_add_hook_removes_kwargs,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\nTest {test.__name__} failed:")
            print_stacktrace(e)
            # On failure, exit with code 1 to signal the issue is present
            sys.exit(1)

    print("All tests passed: Issue appears fixed.")
    sys.exit(0)
```
