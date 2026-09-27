Reasoning:
The issue is that when the status returned from the A2A remote agent is "completed," the server currently still calls _handle_agent_response_and_continue and continues delegating further if next_request is not None. This causes the same request to be sent repeatedly until max turns are reached.

The expected behavior is that once the status is "completed" and a final_result is obtained, the function should immediately return the final_result and not continue sending additional requests.

To fix this, the code should immediately return final_result if the status is "completed" and final_result is not None, thereby avoiding any further delegation loop. For the status "input_required," the existing behavior of continuing delegation might be appropriate since input is awaited.

So, the fix involves adding a conditional partition inside the if a2a_result["status"] in ["completed", "input_required"]: block that:
- If status == "completed" and final_result is not None, return final_result immediately.
- Else if status == "input_required" and final_result is None and next_request is set, continue delegation.

This prevents repeated delegation for completed responses.

This is best fixed by modifying the existing block at the if a2a_result["status"] in ["completed", "input_required"]: in the _delegate_to_a2a function.

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
518                 if a2a_result["status"] == "completed":
519                     if final_result is not None:
520                         return final_result
521                     # if completed but no final_result, stop and return a message or raise error
522                     # to prevent looping
523                     # For safety, just return some message or break
524                     return "A2A completed with no final result."
525 
526                 # status == input_required, continue if next_request exists
527                 if next_request is not None:
528                     current_request = next_request
529                     continue
530 
531                 # no next_request means no further delegation, break loop
532                 break
</patched>
```