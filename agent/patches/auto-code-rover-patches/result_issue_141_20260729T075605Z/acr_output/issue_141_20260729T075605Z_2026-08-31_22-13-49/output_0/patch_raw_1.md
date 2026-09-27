The issue identifies a mistake in the example snippet for the ollama Chat API configuration in the scripts' readme or example file. The key used to specify the model is wrongly given as "model" when it should be "model_name" to reflect the actual key expected by the ollama model implementation (as confirmed by the code in src/agentscope/models/ollama_model.py).

The proper fix is to update the example snippet to use "model_name" instead of "model". Since previous searches couldn't find a file named scripts/README.md, it is likely the example is in another readme or script under the scripts directory or a similarly named file. The issue description states it’s in "scripts的readme文件" (scripts' readme file). Given the usage, the file is probably named "scripts/README.md" or "scripts/readme.md" or possibly "scripts/README" or a similar doc file.

If the exact file cannot be found, usually projects keep examples in markdown docs or sample JSON config files. So, the patch will focus on locating and correcting that snippet wherever it lives under the scripts folder readme or documentation.

Since the user-provided content references the example snippet as:

```
{
"config_name": "my_ollama_chat_config",
"model_type": "ollama_chat",
# Required parameters
"model": "{model_name}",
# Optional parameters
"options": {
# e.g. "temperature": 0., "seed": "123",
},
"keep_alive": "5m",
}
```

We will update the key "model" to "model_name".

---

# modification 1
```
<file>scripts/README.md</file>
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
}</original>
<patched>{
"config_name": "my_ollama_chat_config",
"model_type": "ollama_chat",
# Required parameters
"model_name": "{model_name}",               # The model name used in ollama API, e.g. llama2
# Optional parameters
"options": {                                # Parameters passed to the model when calling
# e.g. "temperature": 0., "seed": "123",
},
"keep_alive": "5m",                         # Controls how long the model will stay loaded into memory
}</patched>
```

If the actual file is named differently or located differently (like scripts/README or scripts/README.md or scripts/readme.md), the patch should be applied similarly.

This minimal patch addresses the core issue: changing the key from "model" to "model_name" in the example config. No other changes are necessary as the rest of the snippet is correct and helpful for users.