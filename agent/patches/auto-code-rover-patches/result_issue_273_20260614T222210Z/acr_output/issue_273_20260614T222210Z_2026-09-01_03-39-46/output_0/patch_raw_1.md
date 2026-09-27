The issue occurs because `get_config(project_path)` might return `None`, especially in a fresh project where the config file is missing. Then, when the code tries to do `config["platform"]`, it raises a `TypeError` since `None` is not subscriptable. To fix this, we should check if `config` is `None` before accessing its keys. If it is `None`, we should raise a clear exception informing the user that the project is not initialized, guiding them to do so.

This change will directly fix the immediate cause of the traceback and provide a user-friendly error message on first-time setup.

No other changes are necessary.

``` 
<file>mle/utils/memory.py</file>
<original>        
22         config = get_config(project_path)
23         if config["platform"] == "OpenAI":
24             self.text_embedding = get_registry().get("openai").create(api_key=config["api_key"])
25         else:
26             raise NotImplementedError
</original>
<patched>        
22         config = get_config(project_path)
23         if config is None:
24             raise RuntimeError(
25                 "Project configuration not found. Please initialize the project before using Memory."
26             )
27         if config["platform"] == "OpenAI":
28             self.text_embedding = get_registry().get("openai").create(api_key=config["api_key"])
29         else:
30             raise NotImplementedError
</patched>
```