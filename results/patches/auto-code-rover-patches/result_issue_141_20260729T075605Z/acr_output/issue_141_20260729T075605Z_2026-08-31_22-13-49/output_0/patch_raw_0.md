Based on the issue description and analysis, the main fix is to update the example snippet for the ollama Chat API in the scripts readme or example files to replace the key "model" with "model_name". Since the requested change is focused on an example snippet (likely a JSON config) in a readme or documentation file, which we have not found explicitly by filename but the issue refers to "scripts的readme文件ollama示例", this patch assumes the relevant file is `scripts/README.md` or a similar markdown or text documentation file in the scripts directory.

The patch will change the JSON snippet example to replace the key `"model": "{model_name}"` with `"model_name": "{model_name}"` as per the issue.

If the example snippet is written in Python or JSON in a file, the patch applies that change accordingly.

---

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
}
</original>
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
}
</patched>
```

---

If the file is not markdown but a python or other format file in scripts folder, the patch can be applied similarly.

If there is no such file but an example Python script or other file under scripts with this snippet, the same key update should be applied there.

This patch corrects the key in the example to 'model_name' to reflect the actual expected key per the ollama_model.py source code. It preserves the rest of the snippet intact.