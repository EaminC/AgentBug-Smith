Reasoning:
The core issue is that `response.metadata.xxx` has inconsistent types for boolean-type keys — sometimes it's a string "true"/"false", sometimes a Python bool True/False. This inconsistency causes bugs downstream because the code expects booleans but occasionally gets strings.

To fix this, the best place is in the parsing/filtering of metadata keys where those key-value pairs are extracted from parsed_response. We can modify the `_filter_content_by_names` method in `DictFilterMixin` to normalize metadata values: if any of the filtered keys are boolean flags (like keys ending with "eliminate", "resurrect", "finish_discussion" used in the werewolf demo), and their values are string literals "true"/"false" (case-insensitive), convert them to Python bool True/False.

This keeps the behavior consistent and ensures downstream code can rely on proper bool types.

We apply this normalization only on the output of `to_metadata()` — i.e., when `keys` is `self.keys_to_metadata` or when `_filter_content_by_names` is called from `to_metadata`. Since `_filter_content_by_names` is used for `to_memory`, `to_content`, and `to_metadata`, but only metadata keys need normalization, a convenient way is to add an internal flag or check in `_filter_content_by_names` to do this normalization only for metadata keys.

Since the calls come from `to_metadata()`, we can pass an extra argument `normalize_metadata_bool` (default False), and call that with True in `to_metadata`.

Alternatively, to keep minimal changes, in `to_metadata` method, after calling `_filter_content_by_names`, we normalize the boolean strings in the returned dict.

This is probably clearer and less intrusive.

Therefore, the patch is:
1. Modify method `to_metadata` to call `_filter_content_by_names` and then normalize the bool strings in the returned metadata dict.
2. Implement a small helper function internally in `DictFilterMixin` for the normalization.

No other changes needed.

---

Patch:

```
<file>src/agentscope/parsers/parser_base.py</file>
<original>    def to_metadata(
        self,
        parsed_response: dict,
        allow_missing: bool = False,
    ) -> Union[str, dict, None]:
        """Filter the fields that will be fed into the returned message
        directly to control the application workflow."""
        return self._filter_content_by_names(
            parsed_response,
            self.keys_to_metadata,
            allow_missing=allow_missing,
        )
</original>
<patched>    def to_metadata(
        self,
        parsed_response: dict,
        allow_missing: bool = False,
    ) -> Union[str, dict, None]:
        """Filter the fields that will be fed into the returned message
        directly to control the application workflow."""
        result = self._filter_content_by_names(
            parsed_response,
            self.keys_to_metadata,
            allow_missing=allow_missing,
        )

        def normalize_bool(val):
            if isinstance(val, str):
                lval = val.lower()
                if lval == "true":
                    return True
                elif lval == "false":
                    return False
            return val

        # normalize boolean string literals to bool in metadata dictionary
        if isinstance(result, dict):
            for k, v in result.items():
                result[k] = normalize_bool(v)
        elif isinstance(result, str):
            # single key case - just normalize the single value
            result = normalize_bool(result)

        return result
</patched>
```