The issue requests adding a "dirty" flag to the JSONSerializableDict to track if any changes have been made to the agent’s state, and then adjusting RepositorySessionManager.sync_agent() to only call update_agent() if the state is dirty or if the internal state has changed.

This avoids unnecessary calls to update_agent(), reducing I/O overhead.

**Reasoning:**

- In JSONSerializableDict:
   - Add _dirty flag initialized as False in __init__.
   - Modify set() and delete() methods to set _dirty to True whenever mutation happens.
   - Add two internal methods _is_dirty() and _clear_dirty().
- In RepositorySessionManager:
   - Add a dict attribute to keep track of the last synced internal_state per agent.
   - In sync_agent(), before calling update_agent(), check if agent.state._is_dirty() or internal_state differs from cached.
   - Only call update_agent() if needed.
   - After successful update_agent(), clear dirty flag and update cached internal_state.
   - On failure, keep the dirty flag set.
   
The `internal_state` is presumably a field in the SessionAgent representing the internal state serialization. Since code uses SessionAgent.from_agent(agent), we can get the current internal_state from the SessionAgent instance created for comparison.

---

# Patch:

```
<file>src/strands/types/json_dict.py</file>
<original>15     def __init__(self, initial_state: dict[str, Any] | None = None):
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
<patched>15     def __init__(self, initial_state: dict[str, Any] | None = None):
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
95         """Return whether this dict has been modified since last cleared."""
96         return self._dirty
97 
98     def _clear_dirty(self) -> None:
99         """Clear the dirty flag (mark as not modified)."""
100        self._dirty = False
</patched>
</file>
```

```
<file>src/strands/session/repository_session_manager.py</file>
<original>27 class RepositorySessionManager(SessionManager):
28     """Session manager for persisting agents in a SessionRepository."""
29 
30     def __init__(
31         self,
32         session_id: str,
33         session_repository: SessionRepository,
34         **kwargs: Any,
35     ):
36         """Initialize the RepositorySessionManager.
...
95     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
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
<patched>27 class RepositorySessionManager(SessionManager):
28     """Session manager for persisting agents in a SessionRepository."""
29 
30     def __init__(
31         self,
32         session_id: str,
33         session_repository: SessionRepository,
34         **kwargs: Any,
35     ):
36         """Initialize the RepositorySessionManager.
...
52         self.session = session
53 
53.1       # Cache for the last synced internal_state per agent_id to check for changes
53.2       self._last_synced_internal_state: dict[str, Any] = {}
54 
55         # Keep track of the latest message of each agent in case we need to redact it.
56         self._latest_agent_message: dict[str, SessionMessage | None] = {}
57 
58     def append_message(self, message: Message, agent: "Agent", **kwargs: Any) -> None:
...
93 
94     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
95         """Serialize and update the agent into the session repository.
96 
97         Args:
98             agent: Agent to sync to the session.
99             **kwargs: Additional keyword arguments for future extensibility.
100         """
100.1        # Create the session agent representation
100.2        session_agent = SessionAgent.from_agent(agent)
100.3        agent_id = agent.agent_id
100.4
100.5        # Get the cached internal_state previously synced for this agent
100.6        last_internal_state = self._last_synced_internal_state.get(agent_id)
100.7
100.8        # Check whether agent.state is dirty or internal_state differs
100.9        if agent.state._is_dirty() or session_agent._internal_state != last_internal_state:
101.0            try:
101.1                self.session_repository.update_agent(self.session_id, session_agent)
101.2            except Exception:
101.3                # sync failed, do not clear dirty flag or update cached internal state
101.4                raise
101.5            else:
101.6                # On success, clear dirty flag and update cached internal state
101.7                agent.state._clear_dirty()
101.8                self._last_synced_internal_state[agent_id] = copy.deepcopy(session_agent._internal_state)
101.9        else:
102.0            # No changes detected, skip update agent call
102.1            pass
</patched>
</file>
```