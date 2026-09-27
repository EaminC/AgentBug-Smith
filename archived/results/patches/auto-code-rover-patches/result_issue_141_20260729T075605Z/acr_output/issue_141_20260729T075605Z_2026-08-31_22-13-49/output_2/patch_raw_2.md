Reasoning:
The issue is that when calling the ollama.chat API and recording the arguments of the invocation, the key for the model name is mistakenly given as "model" when it should be "model_name" according to the specification. This requires changing the key "model" to "model_name" in two places:
1) The call to ollama.chat: replace model=self.model_name with model_name=self.model_name
2) The dictionary passed into self._save_model_invocation: replace "model": self.model_name with "model_name": self.model_name

The rest of the code remains unchanged. No imports are necessary to fix this.

Patch:

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