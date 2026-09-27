The issue mentions that in the Ollama chat API calls and the dictionary that records API arguments, the key used for the model name should be 'model_name' instead of 'model'. In the provided code snippet, the key 'model' is used in both places:

- In the call to `ollama.chat()`
- In the dictionary passed to `_save_model_invocation`

Per the issue's description and intended behavior, these keys need to be replaced with 'model_name' to align with the API specification.

No other code context or logic needs to be changed.

Here is the patch that fixes the keys accordingly:

```
<file>src/agentscope/models/ollama_model.py</file>
<original>        response = ollama.chat(
            model=self.model_name,
            messages=messages,
            options=options,
            keep_alive=keep_alive,
            **kwargs,
        )
...
        self._save_model_invocation(
            arguments={
                "model": self.model_name,
                "messages": messages,
                "options": options,
                "keep_alive": keep_alive,
                **kwargs,
            },
            response=response,
        )</original>
<patched>        response = ollama.chat(
            model_name=self.model_name,
            messages=messages,
            options=options,
            keep_alive=keep_alive,
            **kwargs,
        )
...
        self._save_model_invocation(
            arguments={
                "model_name": self.model_name,
                "messages": messages,
                "options": options,
                "keep_alive": keep_alive,
                **kwargs,
            },
            response=response,
        )</patched>
```