The issue is that toolUse and toolResult events are stored as separate messages, and when listing messages with a limit (default 100), the toolUse event may be dropped but the toolResult event may be kept if it falls within the last 100 messages, causing validation issues during agent hydration. Currently, `_fix_broken_tool_use` adds missing toolResult events for orphaned toolUse events but does not handle orphaned toolResult events that lack a preceding toolUse.

The solution:
- Add a new method `_fix_broken_tool_result` that scans the messages for toolResult events that do not have a preceding corresponding toolUse event.
- For such orphaned toolResult events, insert a dummy toolUse message before them, just like how `_fix_broken_tool_use` adds dummy toolResult content.
- Integrate this new method along with `_fix_broken_tool_use` in the `initialize` method during hydration, so that after loading messages from the session, both corrections are applied.
- Implement a utility `generate_missing_tool_use_content` similar to `generate_missing_tool_result_content` to generate dummy toolUse content blocks.
- This will ensure the toolUse/toolResult events are always paired and aligned in the conversation history, avoiding validation exceptions.

Here is the patch to `RepositorySessionManager` in `repository_session_manager.py`.

```
<file>src/strands/session/repository_session_manager.py</file>
<original>    def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
        """Add tool_result after orphaned tool_use messages.

        Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
        This method retroactively fixes that issue by adding a tool_result outside of session management. After 1.15.0,
        this bug is no longer present.
        """
        for index, message in enumerate(messages):
            # Check all but the latest message in the messages array
            # The latest message being orphaned is handled in the agent class
            if index + 1 < len(messages):
                if any("toolUse" in content for content in message["content"]):
                    tool_use_ids = [
                        content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
                    ]

                    # Check if there are more messages after the current toolUse message
                    tool_result_ids = [
                        content["toolResult"]["toolUseId"]
                        for content in messages[index + 1]["content"]
                        if "toolResult" in content
                    ]

                    missing_tool_use_ids = list(set(tool_use_ids) - set(tool_result_ids))
                    # If there area missing tool use ids, that means the messages history is broken
                    if missing_tool_use_ids:
                        logger.warning(
                            "Session message history has an orphaned toolUse with no toolResult. "
                            "Adding toolResult content blocks to create valid conversation."
                        )
                        # Create the missing toolResult content blocks
                        missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)

                        if tool_result_ids:
                            # If there were any toolResult ids, that means only some of the content blocks are missing
                            messages[index + 1]["content"].extend(missing_content_blocks)
                        else:
                            # The message following the toolUse was not a toolResult, so lets insert it
                            messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
        return messages
</original>
<patched>    def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
        """Add tool_result after orphaned tool_use messages.

        Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
        This method retroactively fixes that issue by adding a tool_result outside of session management. After 1.15.0,
        this bug is no longer present.
        """
        for index, message in enumerate(messages):
            # Check all but the latest message in the messages array
            # The latest message being orphaned is handled in the agent class
            if index + 1 < len(messages):
                if any("toolUse" in content for content in message["content"]):
                    tool_use_ids = [
                        content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
                    ]

                    # Check if there are more messages after the current toolUse message
                    tool_result_ids = [
                        content["toolResult"]["toolUseId"]
                        for content in messages[index + 1]["content"]
                        if "toolResult" in content
                    ]

                    missing_tool_use_ids = list(set(tool_use_ids) - set(tool_result_ids))
                    # If there are missing tool use ids, that means the messages history is broken
                    if missing_tool_use_ids:
                        logger.warning(
                            "Session message history has an orphaned toolUse with no toolResult. "
                            "Adding toolResult content blocks to create valid conversation."
                        )
                        # Create the missing toolResult content blocks
                        missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)

                        if tool_result_ids:
                            # If there were any toolResult ids, that means only some of the content blocks are missing
                            messages[index + 1]["content"].extend(missing_content_blocks)
                        else:
                            # The message following the toolUse was not a toolResult, so lets insert it
                            messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
        return messages

    def _fix_broken_tool_result(self, messages: list[Message]) -> list[Message]:
        """Add tool_use before orphaned tool_result messages.

        This fixes the issue where toolResult messages may appear without preceding toolUse messages,
        by inserting dummy toolUse content blocks before such messages to keep pairing consistent.
        """
        import copy

        # We'll iterate over a copy since we'll be potentially inserting new messages.
        i = 0
        while i < len(messages):
            message = messages[i]
            # If message has toolResult content
            has_tool_result = any("toolResult" in content for content in message["content"])
            if has_tool_result:
                # Collect all toolUseIds referenced by toolResult blocks in this message
                tool_result_ids = [
                    content["toolResult"]["toolUseId"] for content in message["content"] if "toolResult" in content
                ]

                # Check previous message if it has matching toolUseIds
                prev_message = messages[i - 1] if i > 0 else None
                prev_tool_use_ids = []
                if prev_message is not None:
                    prev_tool_use_ids = [
                        content["toolUse"]["toolUseId"] for content in prev_message["content"] if "toolUse" in content
                    ]

                # Determine toolResult ids that have no matching preceding toolUse
                missing_tool_use_ids = [tid for tid in tool_result_ids if tid not in prev_tool_use_ids]

                if missing_tool_use_ids:
                    logger.warning(
                        "Session message history has an orphaned toolResult with no preceding toolUse. "
                        "Inserting missing toolUse content blocks."
                    )
                    missing_tool_use_content = generate_missing_tool_use_content(missing_tool_use_ids)
                    if prev_message is not None:
                        # Append missing toolUse content blocks to previous message's content
                        prev_message["content"].extend(missing_tool_use_content)
                    else:
                        # No previous message, insert a new message with dummy toolUse content before current
                        dummy_message = {"role": "user", "content": missing_tool_use_content}
                        messages.insert(0, dummy_message)
                        i += 1  # Advance index to account for inserted message
            i += 1
        return messages
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
            # Fix orphaned toolResult messages missing toolUse content (new fix)
            agent.messages = self._fix_broken_tool_result(agent.messages)
</patched>
```

```
<file>src/strands/session/repository_session_manager.py</file>
<original>...</original>
<patched>from strands.session.conversation_tool import generate_missing_tool_result_content

def generate_missing_tool_use_content(tool_use_ids: list[str]) -> list[dict]:
    """Generate dummy toolUse content blocks for missing toolUse events."""
    content_blocks = []
    for tool_use_id in tool_use_ids:
        content_blocks.append(
            {
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "status": "success",
                    "content": [{"text": "Dummy toolUse content to fix missing event"}],
                }
            }
        )
    return content_blocks
</patched>
```

Explanation:
- Added the required import of `generate_missing_tool_result_content`.
- Added a new utility function `generate_missing_tool_use_content` that produces dummy toolUse content blocks for the missing toolUse ids.
- Added a new method `_fix_broken_tool_result` in the class to detect orphaned toolResult events without preceding toolUse, and insert dummy toolUse events to fix the sequence.
- Modified `initialize` to call this fix after `_fix_broken_tool_use` to apply both corrections.
This ensures that after hydration, toolUse/toolResult event pairs are complete and no orphaned events remain, preventing the cut off validation error described in the issue.