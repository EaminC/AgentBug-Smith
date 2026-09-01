The issue states that in the Ollama Chat API example, the key `model` should actually be `model_name`. This is to be reflected in the code where the Ollama chat API is called and where the API invocation is recorded. In the provided code, the `__call__` method of the `OllamaChatWrapper` class uses the key `"model"` to pass the model name to `ollama.chat` and in the arguments dictionary passed to `_save_model_invocation`. To fix the issue, we need to replace all instances of `"model"` key with `"model_name"` in these places.

# modification 1
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
        )
</original>
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
        )
</patched>
```