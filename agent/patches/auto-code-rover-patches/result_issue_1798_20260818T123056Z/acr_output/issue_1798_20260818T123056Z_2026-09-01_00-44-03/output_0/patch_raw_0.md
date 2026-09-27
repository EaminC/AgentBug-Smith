The issue requires us to minimize persisting the agent state when no changes have been made. To achieve this:

1. Add a dirty flag `_dirty` to the `JSONSerializableDict` class that tracks if the data has been modified (via `set` or `delete`). Add `_is_dirty()` and `_clear_dirty()` private methods for managing this flag.
2. Modify the `sync_agent` method in `RepositorySessionManager`. It should track the last synced `_internal_state` per agent, and only persist if the agent's state is dirty or its internal state has changed. After a successful update, clear the dirty flag and update the last synced internal state. On failure, keep dirty to ensure retrial.
3. Store the last synced internal state in a dictionary keyed by agent id for correct tracking of multiple agents.

Below is a minimal patch with the necessary changes.

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
17a         self._dirty: bool = False
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
36a         self._dirty = True
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
59a         self._dirty = True
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
95         """Return True if the dict has been modified since last clear."""
96         return self._dirty
97 
98     def _clear_dirty(self) -> None:
99         """Clear the dirty flag, marking the dict as not modified."""
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
101a         # Initialize the cache dict if not yet done
101b         if not hasattr(self, "_last_synced_internal_state"):
101c             self._last_synced_internal_state = {}
102 
102a         agent_id = agent.agent_id
102b         current_internal_state = getattr(agent, "_internal_state", None)
102c         last_internal_state = self._last_synced_internal_state.get(agent_id)
102d 
102e         state_dirty = hasattr(agent.state, "_is_dirty") and callable(getattr(agent.state, "_is_dirty")) and agent.state._is_dirty()
102f         internal_state_changed = current_internal_state != last_internal_state
103 
103a         if state_dirty or internal_state_changed:
103b             try:
103c                 self.session_repository.update_agent(
103d                     self.session_id,
103e                     SessionAgent.from_agent(agent),
103f                 )
103g             except Exception:
103h                 # On failure, keep dirty flag set and do not update cache to retry later
103i                 raise
103j             else:
103k                 # On success, clear the dirty flag and update cached internal state
103l                 if hasattr(agent.state, "_clear_dirty") and callable(getattr(agent.state, "_clear_dirty")):
103m                     agent.state._clear_dirty()
103n                 self._last_synced_internal_state[agent_id] = copy.deepcopy(current_internal_state)
103o         else:
103p             # No changes detected; skip update
103q             pass
</patched>
```