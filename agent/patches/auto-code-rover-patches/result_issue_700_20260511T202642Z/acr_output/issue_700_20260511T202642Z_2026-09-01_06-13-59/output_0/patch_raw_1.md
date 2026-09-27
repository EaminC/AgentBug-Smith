Reasoning:

The issue is that vertex_ai/claude_* models include a version/tag after an '@' sign (for example: `vertex_ai/claude-3-5-sonnet@20240620`), but the `MODEL_SETTINGS` keys for these models use hyphens before the build identifier rather than '@' signs (for example: "claude-3-5-sonnet-20240620").

1. The model string is matched exactly against `MODEL_SETTINGS` entries. Because the '@' sign is used in the model string instead of a hyphen, the exact match fails and falls through to the fallback configurations that do not enable proper edit formats or `use_repo_map`.

2. To fix this, the direct match attempt should normalize '@' to '-' when checking the model name against `MODEL_SETTINGS`. This preserves compatibility for models stored with either '@' or '-' and ensures the proper settings are applied.

3. Additionally, to be consistent and avoid modifying the model string afterward, we can normalize the model string by replacing '@' with '-' right before trying the exact matches.

This minimal patch just adds a normalization step in the `configure_model_settings` method to replace '@' with '-' before matching models in `MODEL_SETTINGS`.

---

Patch:

```
<file>aider/models.py</file>
<original>319     def configure_model_settings(self, model):
320         for ms in MODEL_SETTINGS:
321             # direct match, or match "provider/<model>"
322             if model == ms.name:
323                 for field in fields(ModelSettings):
324                     val = getattr(ms, field.name)
325                     setattr(self, field.name, val)
326                 return  # <--
</original>
<patched>319     def configure_model_settings(self, model):
320         # Normalize model name by replacing '@' with '-'
321         model_normalized = model.replace("@", "-")
322         for ms in MODEL_SETTINGS:
323             # direct match, or match "provider/<model>"
324             if model_normalized == ms.name:
325                 for field in fields(ModelSettings):
326                     val = getattr(ms, field.name)
327                     setattr(self, field.name, val)
328                 return  # <--
</patched>
```

Additionally, because subsequent code uses lowercase model string (`model = model.lower()` at line 328), we must ensure to do that on the normalized model name as well:

So modify the code to be consistent:

```
<file>aider/models.py</file>
<original>328         model = model.lower()

329 
330         if ("llama3" in model or "llama-3" in model) and "70b" in model:
331             self.edit_format = "diff"
332             self.use_repo_map = True
333             self.send_undo_reply = True
334             self.examples_as_sys_msg = True
335             return  # <--
336 
337         if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
338             self.edit_format = "udiff"
339             self.use_repo_map = True
340             self.send_undo_reply = True
341             return  # <--
342 
343         if "gpt-4" in model or "claude-3-opus" in model:
344             self.edit_format = "diff"
345             self.use_repo_map = True
346             self.send_undo_reply = True
347             return  # <--
348 
349         if "gpt-3.5" in model or "gpt-4" in model:
350             self.reminder_as_sys_msg = True
351 
352         # use the defaults
353         if self.edit_format == "diff":
354             self.use_repo_map = True
</original>
<patched>328         model = model_normalized.lower()

329 
330         if ("llama3" in model or "llama-3" in model) and "70b" in model:
331             self.edit_format = "diff"
332             self.use_repo_map = True
333             self.send_undo_reply = True
334             self.examples_as_sys_msg = True
335             return  # <--
336 
337         if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
338             self.edit_format = "udiff"
339             self.use_repo_map = True
340             self.send_undo_reply = True
341             return  # <--
342 
343         if "gpt-4" in model or "claude-3-opus" in model:
344             self.edit_format = "diff"
345             self.use_repo_map = True
346             self.send_undo_reply = True
347             return  # <--
348 
349         if "gpt-3.5" in model or "gpt-4" in model:
350             self.reminder_as_sys_msg = True
351 
352         # use the defaults
353         if self.edit_format == "diff":
354             self.use_repo_map = True
</patched>
```

This minimal fix will allow vertex_ai model names with '@' replaced by '-' to be matched properly in `MODEL_SETTINGS` and avoid fallback to whole-file editing.

---

No changes to `MODEL_SETTINGS` itself are required since the entries already contain the model names with hyphens in place of '@'. This patch adds normalization to allow matching models with '@' in the input string.

# Final patch:
```
<file>aider/models.py</file>
<original>319     def configure_model_settings(self, model):
320         for ms in MODEL_SETTINGS:
321             # direct match, or match "provider/<model>"
322             if model == ms.name:
323                 for field in fields(ModelSettings):
324                     val = getattr(ms, field.name)
325                     setattr(self, field.name, val)
326                 return  # <--
328         model = model.lower()
330         if ("llama3" in model or "llama-3" in model) and "70b" in model:
331             self.edit_format = "diff"
332             self.use_repo_map = True
333             self.send_undo_reply = True
334             self.examples_as_sys_msg = True
335             return  # <--
337         if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
338             self.edit_format = "udiff"
339             self.use_repo_map = True
340             self.send_undo_reply = True
341             return  # <--
343         if "gpt-4" in model or "claude-3-opus" in model:
344             self.edit_format = "diff"
345             self.use_repo_map = True
346             self.send_undo_reply = True
347             return  # <--
349         if "gpt-3.5" in model or "gpt-4" in model:
350             self.reminder_as_sys_msg = True
352         # use the defaults
353         if self.edit_format == "diff":
354             self.use_repo_map = True
</original>
<patched>319     def configure_model_settings(self, model):
320         # Normalize model name by replacing '@' with '-'
321         model_normalized = model.replace("@", "-")
322         for ms in MODEL_SETTINGS:
323             # direct match, or match "provider/<model>"
324             if model_normalized == ms.name:
325                 for field in fields(ModelSettings):
326                     val = getattr(ms, field.name)
327                     setattr(self, field.name, val)
328                 return  # <--
329 
330         model = model_normalized.lower()
331 
332         if ("llama3" in model or "llama-3" in model) and "70b" in model:
333             self.edit_format = "diff"
334             self.use_repo_map = True
335             self.send_undo_reply = True
336             self.examples_as_sys_msg = True
337             return  # <--
338 
339         if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
340             self.edit_format = "udiff"
341             self.use_repo_map = True
342             self.send_undo_reply = True
343             return  # <--
344 
345         if "gpt-4" in model or "claude-3-opus" in model:
346             self.edit_format = "diff"
347             self.use_repo_map = True
348             self.send_undo_reply = True
349             return  # <--
350 
351         if "gpt-3.5" in model or "gpt-4" in model:
352             self.reminder_as_sys_msg = True
353 
354         # use the defaults
355         if self.edit_format == "diff":
356             self.use_repo_map = True
</patched>
```