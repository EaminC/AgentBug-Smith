# Reasoning

The issue arises because the `_normalize_property` function naively sets a default `"type": "string"` on properties that are dicts without `"type"` defined, regardless of whether the property uses a JSON schema union with `"anyOf"`. However, when `"anyOf"` is present, the property may represent complex types such as arrays, objects, or unions including `null`. Setting type to `"string"` in these cases causes incorrect interpretations and tool errors.

To fix this, we simply need to check if `"anyOf"` key is present in the property definition dictionary before setting the default `"type"`. If `"anyOf"` is present, we avoid setting the default `"type"` and leave the property as-is to preserve its complex type definition. For all other cases, the default `"type": "string"` remains. This change preserves all current functionality for normal properties but fixes the problem when `"anyOf"` is used.

No additional imports are required.

---

# Patch

```
<file>src/strands/tools/tools.py</file>
<original>    if "$ref" in normalized_prop:
        return normalized_prop

    normalized_prop.setdefault("type", "string")
    normalized_prop.setdefault("description", f"Property {prop_name}")
    return normalized_prop
</original>
<patched>    if "$ref" in normalized_prop:
        return normalized_prop

    if "anyOf" not in normalized_prop:
        normalized_prop.setdefault("type", "string")
    normalized_prop.setdefault("description", f"Property {prop_name}")
    return normalized_prop
</patched>
```