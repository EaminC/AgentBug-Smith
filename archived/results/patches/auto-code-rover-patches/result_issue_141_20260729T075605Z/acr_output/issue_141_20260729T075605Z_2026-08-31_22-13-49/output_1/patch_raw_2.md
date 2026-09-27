# Reasoning:
The issue points out that in the "scripts" README file, the example for the Ollama chat API uses the key "model" when it should be "model_name" to match the internal API and OllamaChatWrapper class requirements. The patch should correct this key in the example configuration snippet in the relevant README or example file within the scripts directory.

Given that no exact README file was found during the searches, but the issue explicitly mentions the scripts README file for Ollama example, this patch assumes the file exists (likely scripts/ollama_chat_example.py or scripts/README.md or alike). 

The patch replaces occurrences of "model": "{model_name}" with "model_name": "{model_name}" in the scripts' example or README file to fix the documented key.

No changes are needed in the internal OllamaChatWrapper class or source code because it already correctly uses "model_name".

---

# Here is a patch assuming the example is in a file named `scripts/ollama_example.py` (or adjust accordingly if the exact file is known):

```
<file>scripts/ollama_example.py</file>
<original>{
"config_name": "my_ollama_chat_config",
"model_type": "ollama_chat",
# Required parameters
"model": "{model_name}",                    # The model name used in ollama API, e.g. llama2
# Optional parameters
"options": {                                # Parameters passed to the model when calling
# e.g. "temperature": 0., "seed": "123",
},
"keep_alive": "5m",                         # Controls how long the model will stay loaded into memory
}
</original>
<patched>{
"config_name": "my_ollama_chat_config",
"model_type": "ollama_chat",
# Required parameters
"model_name": "{model_name}",                    # The model name used in ollama API, e.g. llama2
# Optional parameters
"options": {                                # Parameters passed to the model when calling
# e.g. "temperature": 0., "seed": "123",
},
"keep_alive": "5m",                         # Controls how long the model will stay loaded into memory
}
</patched>
```

---

If the exact file is known, please replace `scripts/ollama_example.py` accordingly. If instead it is a README.md file, then replace accordingly maintaining the same correction from "model" to "model_name".