The issue is that when `mem0_local_config` is present, the initialization of `self.memory` incorrectly uses `config` instead of `mem0_local_config` to create the Memory instance. This causes mem0 local configuration not to be applied properly, leading to failures like missing API keys when using local embedding providers such as Gemini.

To fix this, the code inside the `else` block on line 50 should be changed from:

```python
self.memory = Memory.from_config(config)
```

to

```python
self.memory = Memory.from_config(mem0_local_config)
```

This change ensures the local mem0 configuration is correctly used when no API key is present.

No other code changes are necessary to solve the issue.

---

Patch:

```
<file>src/crewai/memory/storage/mem0_storage.py</file>
<original>            else:
                if mem0_local_config and len(mem0_local_config):
                    self.memory = Memory.from_config(config)
                else:
                    self.memory = Memory()</original>
<patched>            else:
                if mem0_local_config and len(mem0_local_config):
                    self.memory = Memory.from_config(mem0_local_config)
                else:
                    self.memory = Memory()</patched>
```