The problem arises because deepcopy attempts to pickle/unpickle objects, and _thread.RLock is not picklable. This issue happens when memory=True causes flow state copying using copy.deepcopy(self._state). To fix this, we can customize the deepcopy behavior in the Flow class to exclude or avoid copying unpicklable locks.

The simplest approach is to modify _copy_state to perform shallow copy for the parts of the state known to hold non-picklable locks or to create a custom deepcopy method that ignores those specific attributes.

Since the state is often a BaseModel or dictionary, we can attempt to deepcopy it but override the deepcopy for any attribute known to contain RLocks (possibly by patching __getstate__ / __setstate__ if the state is a BaseModel). However, since we cannot change the BaseModel classes easily, the safer option is to provide a custom deepcopy function that excludes unpickleable locks.

Hence we can replace the _copy_state method to use custom logic:

- Attempt a deepcopy but catch exceptions types related to RLock.
- Alternatively, copy all attributes except those that are RLock or similar thread-related objects.
- Or serialize only picklable fields (like via BaseModel dict export) then reload.

To minimize functional changes, a robust solution is to implement a function to create a deepcopy of the state except skipping over _thread.RLock attributes. Since typical thread locks are used internally and might be on some attributes, skip copying those attributes.

We will implement a helper deepcopy function that skips RLock or any object with attribute __reduce__ raising error.

In the patch, I will:

- Import copy, _thread
- Create a custom deepcopy function e.g., safe_deepcopy that skips RLock objects by returning the object directly (not copying it).
- Modify _copy_state to use safe_deepcopy instead of copy.deepcopy.
- This preserves all other attributes but avoids the thread lock deepcopy issues.

This approach is minimal, focused on the problem, preserves functionality, and only changes _copy_state method.

---

# Patch

```
<file>lib/crewai/src/crewai/flow/flow.py</file>
<original>    def _copy_state(self) -> T:
        return copy.deepcopy(self._state)
</original>
<patched>    import _thread

    def _copy_state(self) -> T:
        def safe_deepcopy(obj, memo=None):
            # Skip deepcopy for unpicklable thread locks
            if memo is None:
                memo = {}

            if isinstance(obj, _thread.RLock):
                # Return the original lock, do not copy
                return obj

            # Handle Pydantic BaseModel by copying dict
            from pydantic import BaseModel
            if isinstance(obj, BaseModel):
                # Dump dict without private attributes then recreate
                try:
                    state_dict = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
                    model_class = type(obj)
                    # Recursively deepcopy the dict
                    copied_dict = safe_deepcopy(state_dict, memo)
                    return model_class(**copied_dict)
                except Exception:
                    # fallback to regular deepcopy
                    pass

            # Handle dicts by deepcopying recursively without locks
            if isinstance(obj, dict):
                return {safe_deepcopy(k, memo): safe_deepcopy(v, memo) for k, v in obj.items()}

            # Handle list/tuple/sets similarly
            if isinstance(obj, list):
                return [safe_deepcopy(i, memo) for i in obj]
            if isinstance(obj, tuple):
                return tuple(safe_deepcopy(i, memo) for i in obj)
            if isinstance(obj, set):
                return {safe_deepcopy(i, memo) for i in obj}

            # Fallback to normal deepcopy
            try:
                return copy.deepcopy(obj, memo)
            except Exception:
                # If deepcopy fails, return the original obj (like for locks etc)
                return obj

        return safe_deepcopy(self._state)
</patched>
```