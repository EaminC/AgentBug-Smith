Reasoning:
The issue states that when using the "gpt-4-turbo" model with vision capability (sending images via the --image_directory flag), images are ignored because vision attribute logic only checks if "vision" is in the model name. The quick fix is to also consider "gpt-4-turbo" and "gpt-4-turbo-2024-04-09" as vision-capable models, explicitly enabling vision for those model names.

This is straightforward: we update the line in the AI class `__init__` method that sets `self.vision` to include a check for those two extra model strings in addition to the existing `"vision" in model_name` condition.

No need to change test files or any other methods; this impacts how vision flag is set which controls the downstream handling of image inputs.

---
Patch:

```
<file>gpt_engineer/core/ai.py</file>
<original>        self.vision = "vision" in model_name</original>
<patched>        self.vision = "vision" in model_name or model_name in ["gpt-4-turbo", "gpt-4-turbo-2024-04-09"]</patched>
```