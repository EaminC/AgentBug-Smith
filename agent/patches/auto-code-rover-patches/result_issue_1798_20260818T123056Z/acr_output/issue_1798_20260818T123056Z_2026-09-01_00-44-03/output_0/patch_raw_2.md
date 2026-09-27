The solution involves two main changes:

1. In `JSONSerializableDict`, we add a private `_dirty` flag initialized to `False`. This flag is set to `True` whenever the state is mutated via `set()` or `delete()`. Two private methods `_is_dirty()` and `_clear_dirty()` are added to check and clear the dirty flag. This satisfies the need to track whether the agent state has been updated.

2. In `RepositorySessionManager.sync_agent()`, we add logic to only call `update_agent()` if either:
   - the agent's state is dirty, or
   - the agent's internal state (`_internal_state`) has changed compared to a cached previous value.
   
   If `update_agent()` is successful, clear the dirty flag and update the cached internal state. If it fails, keep the dirty flag set.

To implement caching of previous internal states per agent, we add a dictionary attribute `_last_synced_internal_state` keyed by `agent.agent_id`.

This approach ensures minimal changes, preserves backwards compatibility, and optimizes syncing by skipping unnecessary updates.

---

Patch:

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
</original>
<patched>15     def __init__(self, initial_state: dict[str, Any] | None = None):
16         """Initialize JSONSerializableDict."""
17         self._data: dict[str, Any]
        self._dirty: bool = False
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
        self._dirty = True
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
        self._dirty = True
+
+    def _is_dirty(self) -> bool:
+        """Return whether the dictionary has been modified since last clear."""
+        return self._dirty
+
+    def _clear_dirty(self) -> None:
+        """Clear the dirty flag after successful sync."""
+        self._dirty = False
</patched>
```

---

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
102         # Initialize storage for last synced internal state if it doesn't exist
103         if not hasattr(self, "_last_synced_internal_state"):
104             self._last_synced_internal_state = {}
105 
106         # Get the agent's current internal state if available, else None
107         current_internal_state = getattr(agent, "_internal_state", None)
108         last_internal_state = self._last_synced_internal_state.get(agent.agent_id)
109 
110         # Check if we need to sync: dirty flag or internal state changed
111         state_dirty = getattr(agent.state, "_is_dirty", lambda: False)()
112         internal_state_changed = current_internal_state != last_internal_state
113 
114         if state_dirty or internal_state_changed:
115             # Attempt the update
116             try:
117                 self.session_repository.update_agent(
118                     self.session_id,
119                     SessionAgent.from_agent(agent),
120                 )
121             except Exception:
122                 # Leave dirty flag set for retry
123                 raise
124             else:
125                 # Clear dirty flag on success and update last synced internal state cache
126                 if hasattr(agent.state, "_clear_dirty"):
127                     agent.state._clear_dirty()
128                 self._last_synced_internal_state[agent.agent_id] = current_internal_state
129         else:
130             # Skip update if no changes
131             pass
</patched>
```