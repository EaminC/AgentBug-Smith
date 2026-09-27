Reasoning:
The problem involves adding a dirty flag to the JSONSerializableDict type to track if its contents have been updated. This flag must be set when `set()` or `delete()` is called.

Additionally, the RepositorySessionManager's `sync_agent()` method needs to be updated so it only calls `update_agent()` if there are changes to the agent's state or if the internal state representation has changed. This requires tracking previously synced internal state per agent.

The steps are:

1. Modify JSONSerializableDict:
   - Add `_dirty` flag initialized to False in __init__.
   - Set `_dirty` to True in `set()` and `delete()`.
   - Add private `_is_dirty()` and `_clear_dirty()` methods for the dirty flag.

2. Modify RepositorySessionManager:
   - Add a new dictionary attribute `_previous_internal_states` to track the last synced internal state per agent_id.
   - In `sync_agent()`, check if either the agent state is dirty or the internal state differs from the last synced value.
   - Only if changed, perform update_agent().
   - On successful update, clear dirty flag and update stored internal state.
   - On failure, keep the dirty flag to allow retry.

This achieves the feature goal of minimizing unnecessary update calls while retaining existing functionality.

---

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
17a        self._dirty: bool = False
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
36a        self._dirty = True
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
59a        self._dirty = True
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
99         """Clear the dirty flag to indicate no pending changes."""
100        self._dirty = False
</patched>
```

# modification 2
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
60a
60b        # Track last synced internal state per agent to avoid unnecessary updates
60c        self._previous_internal_states: dict[str, Any] = {}
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
101a        # Get current agent internal state
101b        current_internal_state = agent._internal_state if hasattr(agent, "_internal_state") else None
101c        agent_state_dirty = getattr(agent.state, "_is_dirty", lambda: False)()
101d
101e        # Retrieve previously synced internal state for this agent
101f        previous_internal_state = self._previous_internal_states.get(agent.agent_id)
101g
101h        # Only sync if state is dirty or internal state has changed
101i        needs_sync = agent_state_dirty or (current_internal_state != previous_internal_state)
101j
101k        if needs_sync:
101l            try:
101m                self.session_repository.update_agent(
101n                    self.session_id,
101o                    SessionAgent.from_agent(agent),
101p                )
101q            except Exception:
101r                # Preserve dirty flag so retry can occur on next sync
101s                raise
101t            else:
101u                # Successful sync: clear dirty flag and update internal state store
101v                if hasattr(agent.state, "_clear_dirty"):
101w                    agent.state._clear_dirty()
101x                self._previous_internal_states[agent.agent_id] = copy.deepcopy(current_internal_state)
101y        else:
101z            # No changes, skipping update_agent
101aa           pass
</patched>
```