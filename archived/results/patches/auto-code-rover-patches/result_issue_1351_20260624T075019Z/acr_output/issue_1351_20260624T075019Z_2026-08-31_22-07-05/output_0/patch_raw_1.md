```
<file>src/agentscope/model/_openai_model.py</file>
<original>                if self.stream_tool_parsing:
                    repaired_input = _json_loads_with_repair(
                        input_str or "{}",
                    )
                    # If the new repaired input is shorter than one in the
                    # last chunk, use the last one to avoid regression
                    last_input = last_input_objs.get(tool_id, {})
                    if len(json.dumps(last_input)) > len(
                        json.dumps(repaired_input),
                    ):
                        repaired_input = last_input
                    last_input_objs[tool_id] = repaired_input
</original>
<patched>                if self.stream_tool_parsing:
                    repaired_input = _json_loads_with_repair(
                        input_str or "{}",
                    )
                    # More robust check to avoid regression due to length comparison only:
                    # Use the repaired input only if it is different and more complete
                    last_input = last_input_objs.get(tool_id, {})

                    def is_complete_json(obj: dict) -> bool:
                        # Basic heuristic: an object is complete if all keys have non-None values
                        if not isinstance(obj, dict):
                            return False
                        for v in obj.values():
                            # We consider None or empty string as incomplete here
                            if v is None:
                                return False
                            if isinstance(v, str) and v.strip() == "":
                                return False
                        return True

                    # If the last input is more complete, keep it; otherwise update
                    if (
                        is_complete_json(last_input)
                        and (len(json.dumps(last_input)) > len(json.dumps(repaired_input)))
                        and not is_complete_json(repaired_input)
                    ):
                        repaired_input = last_input
                    last_input_objs[tool_id] = repaired_input
</patched>
```