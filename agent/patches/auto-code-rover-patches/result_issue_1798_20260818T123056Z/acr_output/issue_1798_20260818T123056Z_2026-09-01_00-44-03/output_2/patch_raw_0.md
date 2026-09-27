Reasoning:

The issue demands introducing a "dirty" flag in JSONSerializableDict so that we can efficiently check if any of its contents have been modified. We'll add a private boolean `_dirty` initialized in `__init__`, set it to True inside `set()` and `delete()`. Also, private helper methods `_is_dirty()` and `_clear_dirty()` will be added.

Then, in RepositorySessionManager's `sync_agent`, we want to avoid redundant calls to `update_agent()` when agent state is unchanged and not dirty. To do this, we have to track the last synced internal state per agent, compare with the current internal state, and check the dirty flag on the agent.state (an instance of JSONSerializableDict). Only when one of those signals a change do we call `update_agent`. After successful update, clear the dirty flag and update the cached internal state for future comparisons. If update fails, keep the dirty flag set.

Implementation details:
- In JSONSerializableDict, add `_dirty` boolean, set on `set()` and `delete()`, and _is_dirty(), _clear_dirty() methods.
- In RepositorySessionManager, add an instance dictionary `_last_synced_internal_state` keyed by agent.agent_id to store last internal states.
- Modify `sync_agent` to use these checks.
- Preserve existing behavior and exception handling.

---

Patch:

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
17.1        self._dirty: bool = False
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
36.1        self._dirty = True
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
59.1        self._dirty = True
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
93.1    def _is_dirty(self) -> bool:
93.2        """Return True if the dict has been modified since last clear."""
93.3        return self._dirty
93.4
93.5    def _clear_dirty(self) -> None:
93.6        """Reset the dirty flag to False."""
93.7        self._dirty = False
</patched>
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
37 
38         If no session with the specified session_id exists yet, it will be created
39         in the session_repository.
40 
41         Args:
42             session_id: ID to use for the session. A new session with this id will be created if it does
43                 not exist in the repository yet
44             session_repository: Underlying session repository to use to store the sessions state.
45             **kwargs: Additional keyword arguments for future extensibility.
46 
47         """
48         self.session_repository = session_repository
49         self.session_id = session_id
50         session = session_repository.read_session(session_id)
51         # Create a session if it does not exist yet
52         if session is None:
53             logger.debug("session_id=<%s> | session not found, creating new session", self.session_id)
54             session = Session(session_id=session_id, session_type=SessionType.AGENT)
55             session_repository.create_session(session)
56 
57         self.session = session
58 
59         # Keep track of the latest message of each agent in case we need to redact it.
60         self._latest_agent_message: dict[str, SessionMessage | None] = {}
61 
62     def append_message(self, message: Message, agent: "Agent", **kwargs: Any) -> None:
63         """Append a message to the agent's session.
64 
65         Args:
66             message: Message to add to the agent in the session
67             agent: Agent to append the message to
68             **kwargs: Additional keyword arguments for future extensibility.
69         """
70         # Calculate the next index (0 if this is the first message, otherwise increment the previous index)
71         latest_agent_message = self._latest_agent_message[agent.agent_id]
72         if latest_agent_message:
73             next_index = latest_agent_message.message_id + 1
74         else:
75             next_index = 0
76 
77         session_message = SessionMessage.from_message(message, next_index)
78         self._latest_agent_message[agent.agent_id] = session_message
79         self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
80 
81     def redact_latest_message(self, redact_message: Message, agent: "Agent", **kwargs: Any) -> None:
82         """Redact the latest message appended to the session.
83 
84         Args:
85             redact_message: New message to use that contains the redact content
86             agent: Agent to apply the message redaction to
87             **kwargs: Additional keyword arguments for future extensibility.
88         """
89         latest_agent_message = self._latest_agent_message[agent.agent_id]
90         if latest_agent_message is None:
91             raise SessionException("No message to redact.")
92         latest_agent_message.redact_message = redact_message
93         return self.session_repository.update_message(self.session_id, agent.agent_id, latest_agent_message)
94 
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
37 
38         If no session with the specified session_id exists yet, it will be created
39         in the session_repository.
40 
41         Args:
42             session_id: ID to use for the session. A new session with this id will be created if it does
43                 not exist in the repository yet
44             session_repository: Underlying session repository to use to store the sessions state.
45             **kwargs: Additional keyword arguments for future extensibility.
46 
47         """
48         self.session_repository = session_repository
49         self.session_id = session_id
50         session = session_repository.read_session(session_id)
51         # Create a session if it does not exist yet
52         if session is None:
53             logger.debug("session_id=<%s> | session not found, creating new session", self.session_id)
54             session = Session(session_id=session_id, session_type=SessionType.AGENT)
55             session_repository.create_session(session)
56 
57         self.session = session
58 
59         # Keep track of the latest message of each agent in case we need to redact it.
60         self._latest_agent_message: dict[str, SessionMessage | None] = {}
61 
61.1        # Keep track of last synced internal state per agent_id for optimization
61.2        self._last_synced_internal_state: dict[str, dict] = {}
61.3
62     def append_message(self, message: Message, agent: "Agent", **kwargs: Any) -> None:
63         """Append a message to the agent's session.
64 
65         Args:
66             message: Message to add to the agent in the session
67             agent: Agent to append the message to
68             **kwargs: Additional keyword arguments for future extensibility.
69         """
70         # Calculate the next index (0 if this is the first message, otherwise increment the previous index)
71         latest_agent_message = self._latest_agent_message[agent.agent_id]
72         if latest_agent_message:
73             next_index = latest_agent_message.message_id + 1
74         else:
75             next_index = 0
76 
77         session_message = SessionMessage.from_message(message, next_index)
78         self._latest_agent_message[agent.agent_id] = session_message
79         self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
80 
81     def redact_latest_message(self, redact_message: Message, agent: "Agent", **kwargs: Any) -> None:
82         """Redact the latest message appended to the session.
83 
84         Args:
85             redact_message: New message to use that contains the redact content
86             agent: Agent to apply the message redaction to
87             **kwargs: Additional keyword arguments for future extensibility.
88         """
89         latest_agent_message = self._latest_agent_message[agent.agent_id]
90         if latest_agent_message is None:
91             raise SessionException("No message to redact.")
92         latest_agent_message.redact_message = redact_message
93         return self.session_repository.update_message(self.session_id, agent.agent_id, latest_agent_message)
94 
95     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
96         """Serialize and update the agent into the session repository.
97 
98         Args:
99             agent: Agent to sync to the session.
100             **kwargs: Additional keyword arguments for future extensibility.
101         """
101.1        # Get the previous internal state stored for this agent
101.2        prev_internal_state = self._last_synced_internal_state.get(agent.agent_id)
101.3
101.4        # Current internal state of agent (usually dict)
101.5        current_internal_state = agent.internal_state if hasattr(agent, "internal_state") else None
101.6
101.7        # Determine if internal state has changed by simple dict comparison, fallback to True if no previous state
101.8        internal_state_changed = False
101.9        if current_internal_state is None:
102.0            internal_state_changed = False  # no internal state means no change to consider here
102.1        elif prev_internal_state is None:
102.2            internal_state_changed = True
102.3        else:
102.4            try:
102.5                internal_state_changed = current_internal_state != prev_internal_state
102.6            except Exception:
102.7                # If comparison fails for any reason, assume changed
102.8                internal_state_changed = True
102.9
103.0        # Check agent.state dirty flag - only if it has _is_dirty()
103.1        is_dirty = False
103.2        if hasattr(agent, "state") and hasattr(agent.state, "_is_dirty"):
103.3            is_dirty = agent.state._is_dirty()
103.4
103.5        # Call update_agent only if dirty or internal state changed
103.6        if is_dirty or internal_state_changed:
103.7            try:
103.8                self.session_repository.update_agent(
103.9                    self.session_id,
103.10                   SessionAgent.from_agent(agent),
103.11               )
103.12               # Clear dirty flag after successful sync (if exists)
103.13               if hasattr(agent, "state") and hasattr(agent.state, "_clear_dirty"):
103.14                   agent.state._clear_dirty()
103.15               # Update cached internal state with a deepcopy to avoid mutation issues
103.16               if current_internal_state is not None:
103.17                   self._last_synced_internal_state[agent.agent_id] = copy.deepcopy(current_internal_state)
103.18               else:
103.19                   # Remove tracked state if none present now
103.20                   self._last_synced_internal_state.pop(agent.agent_id, None)
103.21           except Exception:
103.22               # On failure, keep dirty flag set for retry
103.23               raise
103.24        else:
103.25            # No changes detected, skip update_agent
103.26            pass
</patched>
```