Reasoning:
The issue arises because when a2a_result's status is "completed", the code still proceeds to handle it, potentially assigning next_request and continuing the loop, causing the server agent to delegate again to the same agent repeatedly. The fix is to prevent continuation of delegation after a "completed" status is received and final_result is None. In that case, we should immediately return some result or break the loop. The existing function _handle_agent_response_and_continue might return final_result as None and next_request as something non-None, but for "completed" status, there should not be any continuing delegation. Hence, we must detect this condition and act accordingly: if status is "completed" and final_result is None, we should not continue delegation; instead, return a default message or break to raise an error or end cleanly.

The minimal fix is to add a check: if the status is "completed" and final_result is None (which should not really happen ideally, but can happen due to async or agent response), then break or return. The best is to return some meaningful final message from the existing conversation history or from the response.

I will add this logic just after calling _handle_agent_response_and_continue and before continuing the loop.

---

Patch:

```
<file>lib/crewai/src/crewai/a2a/wrapper.py</file>
<original>            
500             if a2a_result["status"] in ["completed", "input_required"]:
501                 final_result, next_request = _handle_agent_response_and_continue(
502                     self=self,
503                     a2a_result=a2a_result,
504                     agent_id=agent_id,
505                     agent_cards=agent_cards,
506                     a2a_agents=a2a_agents,
507                     original_task_description=original_task_description,
508                     conversation_history=conversation_history,
509                     turn_num=turn_num,
510                     max_turns=max_turns,
511                     task=task,
512                     original_fn=original_fn,
513                     context=context,
514                     tools=tools,
515                     agent_response_model=agent_response_model,
516                 )
517 
518                 if final_result is not None:
519                     return final_result
520 
521                 if next_request is not None:
522                     current_request = next_request
523 
524                 continue
</original>
<patched>            
500             if a2a_result["status"] in ["completed", "input_required"]:
501                 final_result, next_request = _handle_agent_response_and_continue(
502                     self=self,
503                     a2a_result=a2a_result,
504                     agent_id=agent_id,
505                     agent_cards=agent_cards,
506                     a2a_agents=a2a_agents,
507                     original_task_description=original_task_description,
508                     conversation_history=conversation_history,
509                     turn_num=turn_num,
510                     max_turns=max_turns,
511                     task=task,
512                     original_fn=original_fn,
513                     context=context,
514                     tools=tools,
515                     agent_response_model=agent_response_model,
516                 )
517 
518                 if final_result is not None:
519                     return final_result
520 
521                 # If status is 'completed' but final_result is None, do not continue delegation to avoid loop
522                 if a2a_result["status"] == "completed":
523                     # Return the last message from conversation history if possible
524                     for msg in reversed(conversation_history):
525                         if msg.role == Role.agent:
526                             text_parts = [
527                                 part.root.text for part in msg.parts if part.root.kind == "text"
528                             ]
529                             final_message = (
530                                 " ".join(text_parts) if text_parts else "Conversation completed"
531                             )
532                             return final_message
533                     # fallback message
534                     return "Conversation completed"
535 
536                 if next_request is not None:
537                     current_request = next_request
538 
539                 continue
</patched>
```