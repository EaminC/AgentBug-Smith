Reasoning:
1. In `JSONSerializableDict`, we add a `_dirty` flag attribute initialized to False in the constructor. We modify the `set` and `delete` methods to set `_dirty` to True whenever called. We add two private methods `_is_dirty()` to return the dirty flag and `_clear_dirty()` to reset it to False. This provides tracking of whether changes happened in the dict.

2. In `RepositorySessionManager.sync_agent`, we modify to keep a cache (in an instance attribute) of the last synced `_internal_state`. Before calling `update_agent`, we check if the agent's state is dirty (`_is_dirty()`) or if the current `_internal_state` differs from the cached one. Only if either condition is true we call `update_agent`. After a successful update, we clear the dirty flag and update the cached state. If the update fails, we keep the dirty flag set so that a subsequent retry can happen.

This solution matches the problem statement, reduces unnecessary persistence operations, and preserves the existing behavior and error handling.


Patch:

# modification 1
```
<file>src/strands/types/json_dict.py</file>
<original>8 class JSONSerializableDict:
9     """A key-value store with JSON serialization validation.
10 
11     Provides a dict-like interface with automatic validation that all values
12     are JSON serializable on assignment.
13     """
14 
15     def __init__(self, initial_state: dict[str, Any] | None = None):
16         """Initialize JSONSerializableDict."""
17         self._data: dict[str, Any]
18         if initial_state:
19             self._validate_json_serializable(initial_state)
20             self._data = copy.deepcopy(initial_state)
21         else:
22             self._data = {}
23 
24     def set(self, key: str, value: Any) -> None:
25         """Set a value in the store.
26 
27         Args:
28             key: The key to store the value under
29             value: The value to store (must be JSON serializable)
30 
31         Raises:
32             ValueError: If key is invalid, or if value is not JSON serializable
33         """
34         self._validate_key(key)
35         self._validate_json_serializable(value)
36         self._data[key] = copy.deepcopy(value)
37 
38     def get(self, key: str | None = None) -> Any:
39         """Get a value or entire data.
40 
41         Args:
42             key: The key to retrieve (if None, returns entire data dict)
43 
44         Returns:
45             The stored value, entire data dict, or None if not found
46         """
47         if key is None:
48             return copy.deepcopy(self._data)
49         else:
50             return copy.deepcopy(self._data.get(key))
51 
52     def delete(self, key: str) -> None:
53         """Delete a specific key from the store.
54 
55         Args:
56             key: The key to delete
57         """
58         self._validate_key(key)
59         self._data.pop(key, None)
60 
61     def _validate_key(self, key: str) -> None:
62         """Validate that a key is valid.
63 
64         Args:
65             key: The key to validate
66 
67         Raises:
68             ValueError: If key is invalid
69         """
70         if key is None:
71             raise ValueError("Key cannot be None")
72         if not isinstance(key, str):
73             raise ValueError("Key must be a string")
74         if not key.strip():
75             raise ValueError("Key cannot be empty")
76 
77     def _validate_json_serializable(self, value: Any) -> None:
78         """Validate that a value is JSON serializable.
79 
80         Args:
81             value: The value to validate
82 
83         Raises:
84             ValueError: If value is not JSON serializable
85         """
86         try:
87             json.dumps(value)
88         except (TypeError, ValueError) as e:
89             raise ValueError(
90                 f"Value is not JSON serializable: {type(value).__name__}. "
91                 f"Only JSON-compatible types (str, int, float, bool, list, dict, None) are allowed."
92             ) from e
</original>
<patched>8 class JSONSerializableDict:
9     """A key-value store with JSON serialization validation.
10 
11     Provides a dict-like interface with automatic validation that all values
12     are JSON serializable on assignment.
13     """
14 
15     def __init__(self, initial_state: dict[str, Any] | None = None):
16         """Initialize JSONSerializableDict."""
17         self._data: dict[str, Any]
17.1       self._dirty: bool = False
18         if initial_state:
19             self._validate_json_serializable(initial_state)
20             self._data = copy.deepcopy(initial_state)
21         else:
22             self._data = {}
23 
24     def set(self, key: str, value: Any) -> None:
25         """Set a value in the store.
26 
27         Args:
28             key: The key to store the value under
29             value: The value to store (must be JSON serializable)
30 
31         Raises:
32             ValueError: If key is invalid, or if value is not JSON serializable
33         """
34         self._validate_key(key)
35         self._validate_json_serializable(value)
36         self._data[key] = copy.deepcopy(value)
36.1       self._dirty = True
37 
38     def get(self, key: str | None = None) -> Any:
39         """Get a value or entire data.
40 
41         Args:
42             key: The key to retrieve (if None, returns entire data dict)
43 
44         Returns:
45             The stored value, entire data dict, or None if not found
46         """
47         if key is None:
48             return copy.deepcopy(self._data)
49         else:
50             return copy.deepcopy(self._data.get(key))
51 
52     def delete(self, key: str) -> None:
53         """Delete a specific key from the store.
54 
55         Args:
56             key: The key to delete
57         """
58         self._validate_key(key)
59         self._data.pop(key, None)
59.1       self._dirty = True
60 
61     def _validate_key(self, key: str) -> None:
62         """Validate that a key is valid.
63 
64         Args:
65             key: The key to validate
66 
67         Raises:
68             ValueError: If key is invalid
69         """
70         if key is None:
71             raise ValueError("Key cannot be None")
72         if not isinstance(key, str):
73             raise ValueError("Key must be a string")
74         if not key.strip():
75             raise ValueError("Key cannot be empty")
76 
77     def _validate_json_serializable(self, value: Any) -> None:
78         """Validate that a value is JSON serializable.
79 
80         Args:
81             value: The value to validate
82 
83         Raises:
84             ValueError: If value is not JSON serializable
85         """
86         try:
87             json.dumps(value)
88         except (TypeError, ValueError) as e:
89             raise ValueError(
90                 f"Value is not JSON serializable: {type(value).__name__}. "
91                 f"Only JSON-compatible types (str, int, float, bool, list, dict, None) are allowed."
92             ) from e
93 
94     def _is_dirty(self) -> bool:
95         """Return whether the dict has been modified since last clear."""
96         return self._dirty
97 
98     def _clear_dirty(self) -> None:
99         """Reset the dirty flag to False."""
100         self._dirty = False
</patched>
```

# modification 2
```
<file>src/strands/session/repository_session_manager.py</file>
<original>95     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
96         """Serialize and update the agent into the session repository.
97 
98         Args:
99             agent: Agent to sync to the session.
100             **kwargs: Additional keyword arguments for future extensibility.
101         """
102         self.session_repository.update_agent(
103             self.session_id,
104             SessionAgent.from_agent(agent),
105         )
</original>
<patched>95     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
96         """Serialize and update the agent into the session repository.
97 
98         Args:
99             agent: Agent to sync to the session.
100             **kwargs: Additional keyword arguments for future extensibility.
101         """
101.1       if not hasattr(self, '_last_synced_internal_state'):
101.2           self._last_synced_internal_state = {}
101.3
101.4       current_internal_state = getattr(agent, '_internal_state', None)
101.5       # Determine if the agent state or internal_state has changed
101.6       state_dirty = False
101.7       if hasattr(agent.state, '_is_dirty') and callable(agent.state._is_dirty):
101.8           state_dirty = agent.state._is_dirty()
101.9       internal_state_changed = False
101.10      last_state = self._last_synced_internal_state.get(agent.agent_id)
101.11      if current_internal_state != last_state:
101.12          internal_state_changed = True
101.13
101.14      if not state_dirty and not internal_state_changed:
101.15          # No changes detected, skip update
101.16          return
101.17
101.18      try:
101.19          self.session_repository.update_agent(
101.20              self.session_id,
101.21              SessionAgent.from_agent(agent),
101.22          )
101.23      except Exception:
101.24          # On failure keep dirty flag set for retry
101.25          raise
101.26
101.27      # On success, clear dirty flag and update cache
101.28      if hasattr(agent.state, '_clear_dirty') and callable(agent.state._clear_dirty):
101.29          agent.state._clear_dirty()
101.30
101.31      self._last_synced_internal_state[agent.agent_id] = copy.deepcopy(current_internal_state)
</patched>
```