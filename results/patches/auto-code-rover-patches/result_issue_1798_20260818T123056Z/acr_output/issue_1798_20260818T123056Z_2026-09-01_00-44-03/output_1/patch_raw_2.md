The core change is to add a "_dirty" flag to JSONSerializableDict to track if the state has been modified. Then, in RepositorySessionManager.sync_agent, we will keep a cache of the last synced internal state of the agent to detect changes. Before calling update_agent, we check if the current agent state is dirty or if the internal state has changed compared to the last sync. Only then do we call update_agent. We clear the dirty flag only if the update works and keep it set on failure to allow retries. We also update the internal state snapshot after a successful sync.

This approach reduces unnecessary updates and I/O when the agent state hasn't changed but preserves existing behavior and retries on failures.

---

# modification 1
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
17a        self._dirty: bool = False
18         if initial_state:
19             self._validate_json_serializable(initial_state)
20             self._data = copy.deepcopy(initial_state)
20a            self._dirty = False
21         else:
22             self._data = {}
22a            self._dirty = False
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
+
+    def _is_dirty(self) -> bool:
+        """Return True if the dict has been modified since last clear, else False."""
+        return self._dirty
+
+    def _clear_dirty(self) -> None:
+        """Reset the dirty flag to False."""
+        self._dirty = False
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
61 
61a        # Keep track of last synced internal state for agents to avoid redundant update_agent calls
61b        self._last_synced_internal_state: dict[str, dict] = {}
62 
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
101a        agent_id = agent.agent_id
101b        current_internal_state = getattr(agent, "_internal_state", None)
101c        last_synced_state = self._last_synced_internal_state.get(agent_id)
101d        state_dirty = False
101e        # Only access _is_dirty if agent.state has that method (assumed JSONSerializableDict)
101f        if hasattr(agent.state, "_is_dirty") and callable(agent.state._is_dirty):
101g            state_dirty = agent.state._is_dirty()
101h
101i        # Only update if dirty flag set or internal state changed
101j        if not state_dirty and current_internal_state == last_synced_state:
101k            # No changes to persist
101l            return
101m
101n        try:
101o            self.session_repository.update_agent(
101p                self.session_id,
101q                SessionAgent.from_agent(agent),
101r            )
101s            # Clear dirty flag and update last synced internal state after successful sync
101t            if hasattr(agent.state, "_clear_dirty") and callable(agent.state._clear_dirty):
101u                agent.state._clear_dirty()
101v            if current_internal_state is not None:
101w                # Deepcopy to avoid mutation side effects
101x                self._last_synced_internal_state[agent_id] = copy.deepcopy(current_internal_state)
101y            else:
101z                # If no internal state, clear cache entry so subsequent calls won't skip updating unnecessarily
101aa               self._last_synced_internal_state.pop(agent_id, None)
101ab       except Exception:
101ac           # On failure, keep dirty flag so next retry will persist changes
101ad           raise
</patched>
```