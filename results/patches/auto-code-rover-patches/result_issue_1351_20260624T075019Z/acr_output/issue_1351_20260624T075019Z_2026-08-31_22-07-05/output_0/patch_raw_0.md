```
<file>src/agentscope/model/_openai_model.py</file>
<original>
460                     if self.stream_tool_parsing:
461                         repaired_input = _json_loads_with_repair(
462                             input_str or "{}",
463                         )
464                         # If the new repaired input is shorter than one in the
465                         # last chunk, use the last one to avoid regression
466                         last_input = last_input_objs.get(tool_id, {})
467                         if len(json.dumps(last_input)) > len(
468                             json.dumps(repaired_input),
469                         ):
470                             repaired_input = last_input
471                         last_input_objs[tool_id] = repaired_input
</original>
<patched>
460                     if self.stream_tool_parsing:
461                         repaired_input = _json_loads_with_repair(
462                             input_str or "{}",
463                         )
464                         # Use more robust check to avoid regression with partial JSON
465                         last_input = last_input_objs.get(tool_id, {})
466
467                         # Helper function to check whether JSON dict is complete
468                         def is_complete_json(json_obj):
469                             # Basic heuristic: no keys with null or empty values (can be extended)
470                             if not isinstance(json_obj, dict):
471                                 return False
472                             for v in json_obj.values():
473                                 if v is None:
474                                     return False
475                                 if isinstance(v, (str, list, dict)) and len(v) == 0:
476                                     return False
477                             return True
478
479                         last_input_complete = is_complete_json(last_input)
480                         repaired_input_complete = is_complete_json(repaired_input)
481
482                         # Accept repaired input if it is complete; 
483                         # otherwise, if last input is more complete, keep it
484                         if repaired_input_complete:
485                             final_input = repaired_input
486                         elif last_input_complete:
487                             final_input = last_input
488                         else:
489                             # Fall back to length heuristic as fallback if both incomplete
490                             if len(json.dumps(last_input)) > len(json.dumps(repaired_input)):
491                                 final_input = last_input
492                             else:
493                                 final_input = repaired_input
494
495                         repaired_input = final_input
496                         last_input_objs[tool_id] = repaired_input
</patched>
```