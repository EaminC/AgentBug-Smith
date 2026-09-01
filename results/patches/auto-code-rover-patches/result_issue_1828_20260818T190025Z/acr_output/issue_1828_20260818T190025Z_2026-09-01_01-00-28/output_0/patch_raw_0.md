Reasoning:

The main goal is to add an `_is_new_session` flag in `RepositorySessionManager.__init__()` which is set to True if the session is just created and False if it already existed. This flag should then be used in the initialization methods `initialize()`, `initialize_bidi_agent()`, and `initialize_multi_agent()` to skip calls to `read_agent()` or `read_multi_agent()` when the session is new, because for a new session, these API calls will always return None and lead to unnecessary IO calls.

In `initialize()` and `initialize_bidi_agent()`, if `_is_new_session` is True, we'll skip reading the existing agent and directly create the agent and its messages in the session repo.

In `initialize_multi_agent()`, if `_is_new_session` is True, skip the call to `read_multi_agent()` and directly create the multi-agent state.

All other behavior remains unchanged.

---

Patch:

```
<file>src/strands/session/repository_session_manager.py</file>
<original>    def __init__(
        self,
        session_id: str,
        session_repository: SessionRepository,
        **kwargs: Any,
    ):
        """Initialize the RepositorySessionManager.

        If no session with the specified session_id exists yet, it will be created
        in the session_repository.

        Args:
            session_id: ID to use for the session. A new session with this id will be created if it does
                not exist in the repository yet
            session_repository: Underlying session repository to use to store the sessions state.
            **kwargs: Additional keyword arguments for future extensibility.
        """
        self.session_repository = session_repository
        self.session_id = session_id
        session = session_repository.read_session(session_id)
        # Create a session if it does not exist yet
        if session is None:
            logger.debug("session_id=<%s> | session not found, creating new session", self.session_id)
            session = Session(session_id=session_id, session_type=SessionType.AGENT)
            session_repository.create_session(session)

        self.session = session

        # Keep track of the latest message of each agent in case we need to redact it.
        self._latest_agent_message: dict[str, SessionMessage | None] = {}

        # Track the previously synced internal state for each agent to detect changes.
        self._last_synced_internal_state: dict[str, dict[str, Any]] = {}
</original>
<patched>    def __init__(
        self,
        session_id: str,
        session_repository: SessionRepository,
        **kwargs: Any,
    ):
        """Initialize the RepositorySessionManager.

        If no session with the specified session_id exists yet, it will be created
        in the session_repository.

        Args:
            session_id: ID to use for the session. A new session with this id will be created if it does
                not exist in the repository yet
            session_repository: Underlying session repository to use to store the sessions state.
            **kwargs: Additional keyword arguments for future extensibility.
        """
        self.session_repository = session_repository
        self.session_id = session_id
        session = session_repository.read_session(session_id)
        # Create a session if it does not exist yet
        if session is None:
            logger.debug("session_id=<%s> | session not found, creating new session", self.session_id)
            session = Session(session_id=session_id, session_type=SessionType.AGENT)
            session_repository.create_session(session)
            self._is_new_session = True  # NEW: Track new session state
        else:
            self._is_new_session = False  # Session existed, agents may exist

        self.session = session

        # Keep track of the latest message of each agent in case we need to redact it.
        self._latest_agent_message: dict[str, SessionMessage | None] = {}

        # Track the previously synced internal state for each agent to detect changes.
        self._last_synced_internal_state: dict[str, dict[str, Any]] = {}
</patched>
```

```
<file>src/strands/session/repository_session_manager.py</file>
<original>    def initialize(self, agent: "Agent", **kwargs: Any) -> None:
        """Initialize an agent with a session.

        Args:
            agent: Agent to initialize from the session
            **kwargs: Additional keyword arguments for future extensibility.
        """
        if agent.agent_id in self._latest_agent_message:
            raise SessionException("The `agent_id` of an agent must be unique in a session.")
        self._latest_agent_message[agent.agent_id] = None

        session_agent = self.session_repository.read_agent(self.session_id, agent.agent_id)

        if session_agent is None:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | creating agent",
                agent.agent_id,
                self.session_id,
            )

            session_agent = SessionAgent.from_agent(agent)
            self.session_repository.create_agent(self.session_id, session_agent)
            # Initialize messages with sequential indices
            session_message = None
            for i, message in enumerate(agent.messages):
                session_message = SessionMessage.from_message(message, i)
                self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
            self._latest_agent_message[agent.agent_id] = session_message
        else:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | restoring agent",
                agent.agent_id,
                self.session_id,
            )
            agent.state = AgentState(session_agent.state)

            session_agent.initialize_internal_state(agent)

            # Restore the conversation manager to its previous state, and get the optional prepend messages
            prepend_messages = agent.conversation_manager.restore_from_session(session_agent.conversation_manager_state)

            if prepend_messages is None:
                prepend_messages = []

            # List the messages currently in the session, using an offset of the messages previously removed
            # by the conversation manager.
            session_messages = self.session_repository.list_messages(
                session_id=self.session_id,
                agent_id=agent.agent_id,
                offset=agent.conversation_manager.removed_message_count,
            )
            if len(session_messages) > 0:
                self._latest_agent_message[agent.agent_id] = session_messages[-1]

            # Restore the agents messages array including the optional prepend messages
            agent.messages = prepend_messages + [session_message.to_message() for session_message in session_messages]

            # Fix broken session histories: https://github.com/strands-agents/sdk-python/issues/859
            agent.messages = self._fix_broken_tool_use(agent.messages)
</original>
<patched>    def initialize(self, agent: "Agent", **kwargs: Any) -> None:
        """Initialize an agent with a session.

        Args:
            agent: Agent to initialize from the session
            **kwargs: Additional keyword arguments for future extensibility.
        """
        if agent.agent_id in self._latest_agent_message:
            raise SessionException("The `agent_id` of an agent must be unique in a session.")
        self._latest_agent_message[agent.agent_id] = None

        if self._is_new_session:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | creating agent (new session optimization)",
                agent.agent_id,
                self.session_id,
            )
            session_agent = SessionAgent.from_agent(agent)
            self.session_repository.create_agent(self.session_id, session_agent)
            session_message = None
            for i, message in enumerate(agent.messages):
                session_message = SessionMessage.from_message(message, i)
                self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
            self._latest_agent_message[agent.agent_id] = session_message
        else:
            session_agent = self.session_repository.read_agent(self.session_id, agent.agent_id)
            if session_agent is None:
                logger.debug(
                    "agent_id=<%s> | session_id=<%s> | creating agent",
                    agent.agent_id,
                    self.session_id,
                )
                session_agent = SessionAgent.from_agent(agent)
                self.session_repository.create_agent(self.session_id, session_agent)
                session_message = None
                for i, message in enumerate(agent.messages):
                    session_message = SessionMessage.from_message(message, i)
                    self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
                self._latest_agent_message[agent.agent_id] = session_message
            else:
                logger.debug(
                    "agent_id=<%s> | session_id=<%s> | restoring agent",
                    agent.agent_id,
                    self.session_id,
                )
                agent.state = AgentState(session_agent.state)

                session_agent.initialize_internal_state(agent)

                # Restore the conversation manager to its previous state, and get the optional prepend messages
                prepend_messages = agent.conversation_manager.restore_from_session(session_agent.conversation_manager_state)

                if prepend_messages is None:
                    prepend_messages = []

                # List the messages currently in the session, using an offset of the messages previously removed
                # by the conversation manager.
                session_messages = self.session_repository.list_messages(
                    session_id=self.session_id,
                    agent_id=agent.agent_id,
                    offset=agent.conversation_manager.removed_message_count,
                )
                if len(session_messages) > 0:
                    self._latest_agent_message[agent.agent_id] = session_messages[-1]

                # Restore the agents messages array including the optional prepend messages
                agent.messages = prepend_messages + [session_message.to_message() for session_message in session_messages]

                # Fix broken session histories: https://github.com/strands-agents/sdk-python/issues/859
                agent.messages = self._fix_broken_tool_use(agent.messages)
</patched>
```

```
<file>src/strands/session/repository_session_manager.py</file>
<original>    def initialize_bidi_agent(self, agent: "BidiAgent", **kwargs: Any) -> None:
        """Initialize a bidirectional agent with a session.

        Args:
            agent: BidiAgent to initialize from the session
            **kwargs: Additional keyword arguments for future extensibility.
        """
        if agent.agent_id in self._latest_agent_message:
            raise SessionException("The `agent_id` of an agent must be unique in a session.")
        self._latest_agent_message[agent.agent_id] = None

        session_agent = self.session_repository.read_agent(self.session_id, agent.agent_id)

        if session_agent is None:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | creating bidi agent",
                agent.agent_id,
                self.session_id,
            )

            session_agent = SessionAgent.from_bidi_agent(agent)
            self.session_repository.create_agent(self.session_id, session_agent)
            # Initialize messages with sequential indices
            session_message = None
            for i, message in enumerate(agent.messages):
                session_message = SessionMessage.from_message(message, i)
                self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
            self._latest_agent_message[agent.agent_id] = session_message
        else:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | restoring bidi agent",
                agent.agent_id,
                self.session_id,
            )
            agent.state = AgentState(session_agent.state)

            session_agent.initialize_bidi_internal_state(agent)

            # BidiAgent has no conversation_manager, so no prepend_messages or removed_message_count
            session_messages = self.session_repository.list_messages(
                session_id=self.session_id,
                agent_id=agent.agent_id,
                offset=0,
            )
            if len(session_messages) > 0:
                self._latest_agent_message[agent.agent_id] = session_messages[-1]

            # Restore the agents messages array
            agent.messages = [session_message.to_message() for session_message in session_messages]

            # Fix broken session histories: https://github.com/strands-agents/sdk-python/issues/859
            agent.messages = self._fix_broken_tool_use(agent.messages)
</original>
<patched>    def initialize_bidi_agent(self, agent: "BidiAgent", **kwargs: Any) -> None:
        """Initialize a bidirectional agent with a session.

        Args:
            agent: BidiAgent to initialize from the session
            **kwargs: Additional keyword arguments for future extensibility.
        """
        if agent.agent_id in self._latest_agent_message:
            raise SessionException("The `agent_id` of an agent must be unique in a session.")
        self._latest_agent_message[agent.agent_id] = None

        if self._is_new_session:
            logger.debug(
                "agent_id=<%s> | session_id=<%s> | creating bidi agent (new session optimization)",
                agent.agent_id,
                self.session_id,
            )
            session_agent = SessionAgent.from_bidi_agent(agent)
            self.session_repository.create_agent(self.session_id, session_agent)
            session_message = None
            for i, message in enumerate(agent.messages):
                session_message = SessionMessage.from_message(message, i)
                self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
            self._latest_agent_message[agent.agent_id] = session_message
        else:
            session_agent = self.session_repository.read_agent(self.session_id, agent.agent_id)
            if session_agent is None:
                logger.debug(
                    "agent_id=<%s> | session_id=<%s> | creating bidi agent",
                    agent.agent_id,
                    self.session_id,
                )

                session_agent = SessionAgent.from_bidi_agent(agent)
                self.session_repository.create_agent(self.session_id, session_agent)
                session_message = None
                for i, message in enumerate(agent.messages):
                    session_message = SessionMessage.from_message(message, i)
                    self.session_repository.create_message(self.session_id, agent.agent_id, session_message)
                self._latest_agent_message[agent.agent_id] = session_message
            else:
                logger.debug(
                    "agent_id=<%s> | session_id=<%s> | restoring bidi agent",
                    agent.agent_id,
                    self.session_id,
                )
                agent.state = AgentState(session_agent.state)

                session_agent.initialize_bidi_internal_state(agent)

                # BidiAgent has no conversation_manager, so no prepend_messages or removed_message_count
                session_messages = self.session_repository.list_messages(
                    session_id=self.session_id,
                    agent_id=agent.agent_id,
                    offset=0,
                )
                if len(session_messages) > 0:
                    self._latest_agent_message[agent.agent_id] = session_messages[-1]

                # Restore the agents messages array
                agent.messages = [session_message.to_message() for session_message in session_messages]

                # Fix broken session histories: https://github.com/strands-agents/sdk-python/issues/859
                agent.messages = self._fix_broken_tool_use(agent.messages)
</patched>
```

```
<file>src/strands/session/repository_session_manager.py</file>
<original>    def initialize_multi_agent(self, source: "MultiAgentBase", **kwargs: Any) -> None:
        """Initialize multi-agent state from the session repository.

        Args:
            source: Multi-agent source object to restore state into
            **kwargs: Additional keyword arguments for future extensibility.
        """
        state = self.session_repository.read_multi_agent(self.session_id, source.id, **kwargs)
        if state is None:
            self.session_repository.create_multi_agent(self.session_id, source, **kwargs)
        else:
            logger.debug("session_id=<%s> | restoring multi-agent state", self.session_id)
            source.deserialize_state(state)</original>
<patched>    def initialize_multi_agent(self, source: "MultiAgentBase", **kwargs: Any) -> None:
        """Initialize multi-agent state from the session repository.

        Args:
            source: Multi-agent source object to restore state into
            **kwargs: Additional keyword arguments for future extensibility.
        """
        if self._is_new_session:
            # For new sessions, no need to read multi-agent state, just create it
            self.session_repository.create_multi_agent(self.session_id, source, **kwargs)
        else:
            state = self.session_repository.read_multi_agent(self.session_id, source.id, **kwargs)
            if state is None:
                self.session_repository.create_multi_agent(self.session_id, source, **kwargs)
            else:
                logger.debug("session_id=<%s> | restoring multi-agent state", self.session_id)
                source.deserialize_state(state)
</patched>
```