Reasoning:
The issue is that when the server receives a response with status "completed", it still processes `_handle_agent_response_and_continue`, which can return a `next_request`, causing the same request to be delegated again. Since the response is already marked "completed," the delegation loop should stop and return immediately with the `final_result`.

The fix is to adjust the logic inside the loop to avoid continuing delegation when the status is "completed". Specifically, if status is "completed" and a final_result is returned, return it immediately. If status is "completed" but no final_result is returned (which would be odd but possible), do not continue the loop; instead, return something or break to avoid infinite iteration. For `"input_required"`, it's okay to possibly continue if we have a next_request.

Hence, after getting `final_result, next_request`, we should:

- If status is "completed" and final_result is not None, return final_result immediately.
- If status is "completed" and final_result is None, return something appropriate (could be None or empty).
- For "input_required", if final_result is not None, return it; else if next_request is set, continue with the next_request.

Thus, the proposal is to detect if the status is completed and then stop looping immediately, ignoring any next_request. For input_required, the current logic stays.

To do this, we must have access to `a2a_result["status"]` after calling `_handle_agent_response_and_continue`.

This way, we avoid delegating the same completed request again.

The minimal change to the existing code is to re-arrange the logic handling `final_result` and `next_request` inside the block where status is checked.

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
518                 # If status is completed and we have a final result, return it immediately
519                 if a2a_result["status"] == "completed":
520                     if final_result is not None:
521                         return final_result
522                     # Even if final_result is None, don't continue delegating,
523                     # just return None or break (here we choose to return None)
524                     return None
525 
526                 # For input_required, handle continuation logic as before
527                 if final_result is not None:
528                     return final_result
529 
530                 if next_request is not None:
531                     current_request = next_request
532 
533                 continue
</patched>
```