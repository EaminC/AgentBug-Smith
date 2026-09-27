```python
# reproducer.py

def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    import sys

    try:
        # Try to import the Model interface and check estimate_tokens method availability
        from model import Model  # Adjust 'model' import as per your SDK structure
        from typing import Optional, List
        from abc import ABC
        try:
            # Check if estimate_tokens method is defined exactly as specified
            import inspect

            sig_expected = "(self, messages, tool_specs=None, system_prompt=None)"
            if not hasattr(Model, "estimate_tokens"):
                raise AssertionError("Model class missing 'estimate_tokens' method")

            est_method = Model.estimate_tokens
            if not callable(est_method):
                raise AssertionError("'estimate_tokens' is not callable")

            # Inspect the signature - ignore annotations for looseness
            sig = inspect.signature(est_method)
            param_names = list(sig.parameters.keys())
            expected_param_names = ["self", "messages", "tool_specs", "system_prompt"]
            if param_names != expected_param_names:
                raise AssertionError(
                    f"'estimate_tokens' parameter names mismatch. "
                    f"Expected {expected_param_names}, got {param_names}"
                )

            # Check default values for optional parameters
            tool_specs_default = sig.parameters["tool_specs"].default
            system_prompt_default = sig.parameters["system_prompt"].default
            from inspect import _empty
            if tool_specs_default is _empty:
                raise AssertionError("'tool_specs' parameter missing default value None")
            if system_prompt_default is not None:
                raise AssertionError("'system_prompt' parameter default should be None")

            # Try calling estimate_tokens on a concrete model instance
            # Here we try to import a concrete model implementation, e.g. OpenAIModel
            try:
                from openai_model import OpenAIModel  # Adjust as per your SDK
            except ImportError:
                # fallback: try any subclass of Model that can be constructed with no args
                subclasses = Model.__subclasses__()
                instance = None
                for c in subclasses:
                    try:
                        instance = c()
                        break
                    except Exception:
                        continue
                if instance is None:
                    raise AssertionError("No concrete Model subclass constructible without arguments found")

            else:
                instance = OpenAIModel()

            # Prepare dummy parameters
            # dummy Messages type - just a list of dict or similar
            messages = [{"role": "user", "content": "Hello"}]

            # Call estimate_tokens and expect int result
            result = instance.estimate_tokens(messages)
            if not isinstance(result, int):
                raise AssertionError(f"estimate_tokens did not return int, returned {type(result)}")

        except Exception as e:
            raise AssertionError(
                f"estimate_tokens method missing or does not conform to specification: {e}"
            ) from e

    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

    print("estimate_tokens method present and works as expected.")
    sys.exit(0)
```
