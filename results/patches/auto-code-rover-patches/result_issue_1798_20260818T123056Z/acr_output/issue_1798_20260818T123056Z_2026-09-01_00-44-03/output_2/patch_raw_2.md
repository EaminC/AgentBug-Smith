Reasoning:
1. In `JSONSerializableDict`, add a private boolean `_dirty` initialized to False in `__init__`. Then set `_dirty` to True inside `set()` and `delete()` since these operations modify the dictionary.
2. Add private methods `_is_dirty()` to return `_dirty` status, and `_clear_dirty()` to clear the dirty flag.
3. In `RepositorySessionManager`, add an attribute to track the last known internal state of each agent synced. This can be a dictionary keyed by agent_id.
4. Modify `sync_agent()` to first check if the agent's state is dirty or if the internal state has changed compared to the last synced one.
5. Only call `update_agent()` if either condition is true.
6. After successful update, clear the dirty flag and update tracked internal state.
7. If the update fails, leave dirty flag as is for retry on next sync.

This approach ensures that unnecessary `update_agent()` calls are skipped when no relevant state change occurred, and dirty flags are only cleared after successful sync.

---

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
18         self._dirty: bool = False
19         if initial_state:
20             self._validate_json_serializable(initial_state)
21             self._data = copy.deepcopy(initial_state)
22         else:
23             self._data = {}
24 
25     def set(self, key: str, value: Any) -> None:
26         """Set a value in the store.
27 
28         Args:
29             key: The key to store the value under
30             value: The value to store (must be JSON serializable)
31 
32         Raises:
33             ValueError: If key is invalid, or if value is not JSON serializable
34         """
35         self._validate_key(key)
36         self._validate_json_serializable(value)
37         self._data[key] = copy.deepcopy(value)
38         self._dirty = True
39 
40     def get(self, key: str | None = None) -> Any:
41         """Get a value or entire data.
42 
43         Args:
44             key: The key to retrieve (if None, returns entire data dict)
45 
46         Returns:
47             The stored value, entire data dict, or None if not found
48         """
49         if key is None:
50             return copy.deepcopy(self._data)
51         else:
52             return copy.deepcopy(self._data.get(key))
53 
54     def delete(self, key: str) -> None:
55         """Delete a specific key from the store.
56 
57         Args:
58             key: The key to delete
59         """
60         self._validate_key(key)
61         self._data.pop(key, None)
62         self._dirty = True
63 
64     def _validate_key(self, key: str) -> None:
65         """Validate that a key is valid.
66 
67         Args:
68             key: The key to validate
69 
70         Raises:
71             ValueError: If key is invalid
72         """
73         if key is None:
74             raise ValueError("Key cannot be None")
75         if not isinstance(key, str):
76             raise ValueError("Key must be a string")
77         if not key.strip():
78             raise ValueError("Key cannot be empty")
79 
80     def _validate_json_serializable(self, value: Any) -> None:
81         """Validate that a value is JSON serializable.
82 
83         Args:
84             value: The value to validate
85 
86         Raises:
87             ValueError: If value is not JSON serializable
88         """
89         try:
90             json.dumps(value)
91         except (TypeError, ValueError) as e:
92             raise ValueError(
93                 f"Value is not JSON serializable: {type(value).__name__}. "
94                 f"Only JSON-compatible types (str, int, float, bool, list, dict, None) are allowed."
95             ) from e
96 
97     def _is_dirty(self) -> bool:
98         """Check whether this dict has been modified since last clear."""
99         return self._dirty
100
101    def _clear_dirty(self) -> None:
102        """Clear the dirty flag after a successful sync."""
103        self._dirty = False
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
61         # Track previously synced internal state of agents by agent_id
62         self._last_synced_internal_state: dict[str, dict[str, Any]] = {}
63 
64     def append_message(self, message: Message, agent: "Agent", **kwargs: Any) -> None:
65         """Append a message to the agent's session.
66 
67         Args:
68             message: Message to add to the agent in the session
69             agent: Agent to append the message to
70             **kwargs: Additional keyword arguments for future extensibility.
71         """
72         # Calculate the next index (0 if this is the first message, otherwise increment the previous index)
73         latest_agent_message = self._latest_agent_message[agent.agent_id]
74         if latest_agent_message:
75             next_index = latest_agent_message.message_id + 1
76         else:
77             next_index = 0
78 
79         session_message = SessionMessage.from_message(message, next_index)
80         self._latest_agent_message[agent.agent_id] = session_message
81         self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
82 
83     def redact_latest_message(self, redact_message: Message, agent: "Agent", **kwargs: Any) -> None:
84         """Redact the latest message appended to the session.
85 
86         Args:
87             redact_message: New message to use that contains the redact content
88             agent: Agent to apply the message redaction to
89             **kwargs: Additional keyword arguments for future extensibility.
90         """
91         latest_agent_message = self._latest_agent_message[agent.agent_id]
92         if latest_agent_message is None:
93             raise SessionException("No message to redact.")
94         latest_agent_message.redact_message = redact_message
95         return self.session_repository.update_message(self.session_id, agent.agent_id, latest_agent_message)
96 
97     def sync_agent(self, agent: "Agent", **kwargs: Any) -> None:
98         """Serialize and update the agent into the session repository.
99 
100        Args:
101            agent: Agent to sync to the session.
102            **kwargs: Additional keyword arguments for future extensibility.
103        """
104        agent_id = agent.agent_id
105        # Defensive: if agent.state does not have _is_dirty method, assume dirty = True to be safe
106        is_state_dirty = False
107        if hasattr(agent.state, "_is_dirty") and callable(agent.state._is_dirty):
108            is_state_dirty = agent.state._is_dirty()
109        else:
110            is_state_dirty = True
111
112        # Get current internal state from agent's internal attribute if exists, else empty dict
113        current_internal_state = None
114        # Some SessionAgent.from_agent may initialize internal state on the agent/state for comparison
115        # We try to get the internal state dict attribute if it exists: assume agent has attribute _internal_state for tracking
116        # Else fallback to empty dict
117        internal_state_attr = "_internal_state"
118        if hasattr(agent, internal_state_attr):
119            current_internal_state = getattr(agent, internal_state_attr)
120            if current_internal_state is None:
121                current_internal_state = {}
122            # Defensive copy to avoid accidental modifications
123            else:
124                current_internal_state = copy.deepcopy(current_internal_state)
125        else:
126            # For safety fallback
127            current_internal_state = {}
128
129        last_synced_state = self._last_synced_internal_state.get(agent_id, {})
130
131        # Compare internal states for difference
132        internal_state_changed = current_internal_state != last_synced_state
133
134        # Only sync if state is dirty or internal state changed
135        if is_state_dirty or internal_state_changed:
136            try:
137                self.session_repository.update_agent(
138                    self.session_id,
139                    SessionAgent.from_agent(agent),
140                )
141            except Exception:
142                # Do not clear dirty flag, so that sync will retry later
143                raise
144            else:
145                # On successful sync clear dirty flag and update tracked internal state
146                if hasattr(agent.state, "_clear_dirty") and callable(agent.state._clear_dirty):
147                    agent.state._clear_dirty()
148                self._last_synced_internal_state[agent_id] = current_internal_state
149
150        else:
151            # No update needed (state clean and internal state not changed)
152            pass
</patched>
```