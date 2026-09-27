Reasoning:
The main problem is that when a2a_result["status"] is "completed", the server agent unnecessarily continues the loop by calling _handle_agent_response_and_continue, and only stops when the max_turn limit is reached, causing repeated delegation.

This indicates that the handling inside _handle_agent_response_and_continue might not be returning a final_result when the a2a response corresponds to a "completed" state. 
Also, in _delegate_to_a2a, the loop should break immediately when final_result is not None, which seems right in the current logic.

However, looking into _handle_agent_response_and_continue, it decides the final_result and next_request based on the is_a2a field in the response. If is_a2a is True, it returns None, next_request (indicating continuation). But if the status is "completed" (from a2a_result), then regardless of the is_a2a value, the method should return a final_result to stop the multi-turn delegation.

Therefore, the fix is to enhance _handle_agent_response_and_continue to detect if the a2a_result status is "completed" and return the final_result accordingly, even if is_a2a is True.

Specifically, we should add logic in _handle_agent_response_and_continue to check if the current a2a_result's status is "completed", and if so, return final_result and None to stop.

The rest of the logic in _delegate_to_a2a appears correct, since it breaks if final_result is not None.

Patch:

- Modify _handle_agent_response_and_continue to accept the "status" field from a2a_result, and when status == "completed", return final_result, None unconditionally.
- To do this cleanly, add a parameter `a2a_status` to _handle_agent_response_and_continue.
- Adjust the caller in _delegate_to_a2a to pass this status.
- Then in _handle_agent_response_and_continue, if a2a_status == "completed", return the final_result with None next_request.
- Otherwise preserve existing behavior.
- This avoids the loop continuing when completed.

---

# modification 1

```
<file>lib/crewai/src/crewai/a2a/wrapper.py</file>
<original>def _handle_agent_response_and_continue(
    self: Agent,
    a2a_result: dict[str, Any],
    agent_id: str,
    agent_cards: dict[str, AgentCard] | None,
    a2a_agents: list[A2AConfig],
    original_task_description: str,
    conversation_history: list[Message],
    turn_num: int,
    max_turns: int,
    task: Task,
    original_fn: Callable[..., str],
    context: str | None,
    tools: list[BaseTool] | None,
    agent_response_model: type[BaseModel],
) -> tuple[str | None, str | None]:
    """Handle A2A result and get CrewAI agent's response.

    Args:
        self: The agent instance
        a2a_result: Result from A2A delegation
        agent_id: ID of the A2A agent
        agent_cards: Pre-fetched agent cards
        a2a_agents: List of A2A configurations
        original_task_description: Original task description
        conversation_history: Conversation history
        turn_num: Current turn number
        max_turns: Maximum turns allowed
        task: The task being executed
        original_fn: Original execute_task method
        context: Optional context
        tools: Optional tools
        agent_response_model: Response model for parsing

    Returns:
        Tuple of (final_result, current_request) where:
        - final_result is not None if conversation should end
        - current_request is the next message to send if continuing
    """
    agent_cards_dict = agent_cards or {}
    if "agent_card" in a2a_result and agent_id not in agent_cards_dict:
        agent_cards_dict[agent_id] = a2a_result["agent_card"]

    task.description = _augment_prompt_with_a2a(
        a2a_agents=a2a_agents,
        task_description=original_task_description,
        conversation_history=conversation_history,
        turn_num=turn_num,
        max_turns=max_turns,
        agent_cards=agent_cards_dict,
    )

    raw_result = original_fn(self, task, context, tools)
    llm_response = _parse_agent_response(
        raw_result=raw_result, agent_response_model=agent_response_model
    )

    if isinstance(llm_response, BaseModel) and isinstance(
        llm_response, AgentResponseProtocol
    ):
        if not llm_response.is_a2a:
            final_turn_number = turn_num + 1
            crewai_event_bus.emit(
                None,
                A2AMessageSentEvent(
                    message=str(llm_response.message),
                    turn_number=final_turn_number,
                    is_multiturn=True,
                    agent_role=self.role,
                ),
            )
            crewai_event_bus.emit(
                None,
                A2AConversationCompletedEvent(
                    status="completed",
                    final_result=str(llm_response.message),
                    error=None,
                    total_turns=final_turn_number,
                ),
            )
            return str(llm_response.message), None
        return None, str(llm_response.message)

    return str(raw_result), None
</original>
<patched>def _handle_agent_response_and_continue(
    self: Agent,
    a2a_result: dict[str, Any],
    agent_id: str,
    agent_cards: dict[str, AgentCard] | None,
    a2a_agents: list[A2AConfig],
    original_task_description: str,
    conversation_history: list[Message],
    turn_num: int,
    max_turns: int,
    task: Task,
    original_fn: Callable[..., str],
    context: str | None,
    tools: list[BaseTool] | None,
    agent_response_model: type[BaseModel],
    a2a_status: str = None,
) -> tuple[str | None, str | None]:
    """Handle A2A result and get CrewAI agent's response.

    Args:
        self: The agent instance
        a2a_result: Result from A2A delegation
        agent_id: ID of the A2A agent
        agent_cards: Pre-fetched agent cards
        a2a_agents: List of A2A configurations
        original_task_description: Original task description
        conversation_history: Conversation history
        turn_num: Current turn number
        max_turns: Maximum turns allowed
        task: The task being executed
        original_fn: Original execute_task method
        context: Optional context
        tools: Optional tools
        agent_response_model: Response model for parsing
        a2a_status: The status from a2a_result (optional)

    Returns:
        Tuple of (final_result, current_request) where:
        - final_result is not None if conversation should end
        - current_request is the next message to send if continuing
    """
    agent_cards_dict = agent_cards or {}
    if "agent_card" in a2a_result and agent_id not in agent_cards_dict:
        agent_cards_dict[agent_id] = a2a_result["agent_card"]

    task.description = _augment_prompt_with_a2a(
        a2a_agents=a2a_agents,
        task_description=original_task_description,
        conversation_history=conversation_history,
        turn_num=turn_num,
        max_turns=max_turns,
        agent_cards=agent_cards_dict,
    )

    raw_result = original_fn(self, task, context, tools)
    llm_response = _parse_agent_response(
        raw_result=raw_result, agent_response_model=agent_response_model
    )

    # New logic: if status is "completed", return final_result unconditionally to stop delegation
    if a2a_status == "completed":
        return str(raw_result), None

    if isinstance(llm_response, BaseModel) and isinstance(
        llm_response, AgentResponseProtocol
    ):
        if not llm_response.is_a2a:
            final_turn_number = turn_num + 1
            crewai_event_bus.emit(
                None,
                A2AMessageSentEvent(
                    message=str(llm_response.message),
                    turn_number=final_turn_number,
                    is_multiturn=True,
                    agent_role=self.role,
                ),
            )
            crewai_event_bus.emit(
                None,
                A2AConversationCompletedEvent(
                    status="completed",
                    final_result=str(llm_response.message),
                    error=None,
                    total_turns=final_turn_number,
                ),
            )
            return str(llm_response.message), None
        return None, str(llm_response.message)

    return str(raw_result), None
</patched>
</file>
```

# modification 2
```
<file>lib/crewai/src/crewai/a2a/wrapper.py</file>
<original>            final_result, next_request = _handle_agent_response_and_continue(
                self=self,
                a2a_result=a2a_result,
                agent_id=agent_id,
                agent_cards=agent_cards,
                a2a_agents=a2a_agents,
                original_task_description=original_task_description,
                conversation_history=conversation_history,
                turn_num=turn_num,
                max_turns=max_turns,
                task=task,
                original_fn=original_fn,
                context=context,
                tools=tools,
                agent_response_model=agent_response_model,
            )
</original>
<patched>            final_result, next_request = _handle_agent_response_and_continue(
                self=self,
                a2a_result=a2a_result,
                agent_id=agent_id,
                agent_cards=agent_cards,
                a2a_agents=a2a_agents,
                original_task_description=original_task_description,
                conversation_history=conversation_history,
                turn_num=turn_num,
                max_turns=max_turns,
                task=task,
                original_fn=original_fn,
                context=context,
                tools=tools,
                agent_response_model=agent_response_model,
                a2a_status=a2a_result.get("status"),
            )
</patched>
</file>
```