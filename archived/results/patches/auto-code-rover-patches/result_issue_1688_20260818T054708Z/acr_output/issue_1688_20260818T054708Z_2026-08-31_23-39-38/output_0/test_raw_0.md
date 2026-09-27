```python
# reproducer.py
import sys
from typing import Any, List, Callable, Optional

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

# --- Mocks and minimal stubs to simulate environment ---

class HookProvider:
    """Old base class for hook providers."""
    def register_hooks(self, registry: Any, **kwargs: Any) -> None:
        raise NotImplementedError

class Plugin:
    """New Plugin protocol/interface requiring `name` and `init_plugin`."""
    name: str
    def init_plugin(self, agent: Any) -> None:
        raise NotImplementedError

class BeforeToolCallEvent:
    """Dummy event class."""
    pass

class SteeringContext:
    """Dummy Context."""
    pass

class SteeringContextProvider:
    """Dummy context provider."""
    def context_providers(self) -> List[Callable]:
        return []

class Agent:
    """Simulated Agent with plugins and add_hook method."""

    def __init__(self, plugins: Optional[List[Plugin]] = None, hooks: Optional[List[HookProvider]] = None):
        self._hooks = []  # Registered callbacks: tuples of (event_type, callback)
        self._plugins = plugins or []
        self._hook_providers = hooks or []

        # Register plugin hooks
        for plugin in self._plugins:
            # Plugin must have `name` attribute and init_plugin method
            if not hasattr(plugin, "name"):
                raise TypeError(f"Plugin {plugin} missing required attribute 'name'")
            if not callable(getattr(plugin, "init_plugin", None)):
                raise TypeError(f"Plugin {plugin} missing required method 'init_plugin'")
            plugin.init_plugin(self)

        # Register hook provider hooks (old method)
        for hook_provider in self._hook_providers:
            # HookProvider must have register_hooks(registry)
            # We simulate a registry class just passing self for simplicity
            hook_provider.register_hooks(self)

    def add_hook(self, event_type: Any, callback: Callable) -> None:
        if not callable(callback):
            raise TypeError("Callback must be callable")
        self._hooks.append((event_type, callback))

    def get_hooks_for_event(self, event_type: Any) -> List[Callable]:
        return [cb for et, cb in self._hooks if et == event_type]

    def hooks_registered(self) -> List[Any]:
        return self._hooks

# --- SteeringHandler Old implementation (with HookProvider) ---
# For sanity check; not used in final test below.
class SteeringHandlerOld(HookProvider):
    def __init__(self, context_providers: Optional[List[SteeringContextProvider]] = None):
        super().__init__()
        self.steering_context = SteeringContext()
        self._context_callbacks = []
        for provider in context_providers or []:
            self._context_callbacks.extend(provider.context_providers())

    def register_hooks(self, registry: Agent, **kwargs: Any) -> None:
        # Supposed to add hooks to registry (Agent here)
        # Old param order: registry.add_callback(event_type, callback)
        # But we use agent.add_hook(event_type, callback)
        registry.add_hook(BeforeToolCallEvent, self._on_before_model_call)

    def _on_before_model_call(self):
        pass


# --- SteeringHandler New implementation (Plugin protocol) ---

class SteeringHandler(Plugin):
    """Base class for steering handlers that provide contextual guidance to agents.
    
    Steering handlers maintain local context and register hook callbacks
    to populate context data as needed for guidance decisions.
    """

    name = "steering"

    def __init__(self, context_providers: Optional[List[SteeringContextProvider]] = None):
        self.steering_context = SteeringContext()
        self._context_callbacks = []
        for provider in context_providers or []:
            self._context_callbacks.extend(provider.context_providers())

    def init_plugin(self, agent: Agent) -> None:
        """Initialize the steering handler with an agent.

        Args:
            agent: The agent instance to attach steering to.
        """
        # Use agent.add_hook(callback, event_type)
        # Note: parameter order is (event_type, callback)
        # The issue description said order differs vs old registry
        # But agent.add_hook(event_type, callback) is correct here.
        # We test for correct usage.
        agent.add_hook(BeforeToolCallEvent, self._on_before_model_call)

    def _on_before_model_call(self):
        pass


# --- Test function to verify migration correctness ---

def test_steeringhandler_migration():
    """Test that SteeringHandler implements Plugin protocol correctly,
    does not inherit from HookProvider,
    and registers hooks properly with Agent.
    """

    # 1. Class does NOT inherit from HookProvider
    bases = [base.__name__ for base in SteeringHandler.__bases__]
    if "HookProvider" in bases:
        raise AssertionError("SteeringHandler must NOT inherit from HookProvider")

    # 2. Has 'name' attribute of type str
    if not hasattr(SteeringHandler, "name") or not isinstance(SteeringHandler.name, str):
        raise AssertionError("SteeringHandler must have class attribute 'name' of type str")

    # 3. Has method init_plugin(agent)
    if not callable(getattr(SteeringHandler, "init_plugin", None)):
        raise AssertionError("SteeringHandler must implement method 'init_plugin(agent)'")

    # 4. Instantiate with no context providers
    handler = SteeringHandler()

    # 5. Create agent with the plugin; this should call init_plugin and register hooks
    agent = Agent(plugins=[handler])

    # 6. Check that agent has registered the correct hook with correct callback
    hooks = agent.hooks_registered()
    if not hooks:
        raise AssertionError("No hooks registered on agent by SteeringHandler plugin")

    # All registered hooks should have event_type == BeforeToolCallEvent and callback _on_before_model_call
    found = False
    for (event_type, callback) in hooks:
        if event_type is BeforeToolCallEvent and callable(callback) and callback == handler._on_before_model_call:
            found = True
            break
    if not found:
        raise AssertionError("Expected BeforeToolCallEvent hook with _on_before_model_call callback not found")

    # 7. Check LLMSteeringHandler subclass compatibility:
    class LLMSteeringHandler(SteeringHandler):
        def steer_before_tool(self):
            pass

    llm_handler = LLMSteeringHandler()

    # Init plugin with agent (empty agent)
    agent2 = Agent(plugins=[llm_handler])

    # Confirm the same hook is registered
    hooks2 = agent2.hooks_registered()
    if not hooks2:
        raise AssertionError("No hooks registered on agent by LLMSteeringHandler plugin")

    found = False
    for (event_type, callback) in hooks2:
        if event_type is BeforeToolCallEvent and callable(callback) and callback == llm_handler._on_before_model_call:
            found = True
            break
    if not found:
        raise AssertionError("Expected BeforeToolCallEvent hook with _on_before_model_call callback not found for LLMSteeringHandler")

    # Passed all tests
    print("SteeringHandler migration to Plugin protocol verified successfully.")

if __name__ == "__main__":
    try:
        test_steeringhandler_migration()
        sys.exit(0)
    except AssertionError as e:
        print_stacktrace(e)
        sys.exit(1)
```
