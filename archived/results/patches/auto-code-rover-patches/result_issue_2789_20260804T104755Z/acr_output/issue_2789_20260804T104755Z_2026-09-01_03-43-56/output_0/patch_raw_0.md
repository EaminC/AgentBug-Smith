Reasoning:
The issue arises because, when passing context as an empty list (or any non-string falsy value) explicitly to execute_task(), the condition `if context:` in the method still evaluates to True (because an empty list is truthy in Python when converted to string or in some usage), or more accurately the context is passed mistakenly, which causes the task prompt to include context that comes from previous tasks or other sources.

The fix involves explicitly checking if the context parameter is not None and is a string (or at least permissive of string types) before augmenting the task prompt with context. If the context is an empty list or any falsy but not a string (like empty list or false), it should be treated as no context (i.e., skip appending the context).

Also, in ContextualMemory.build_context_for_task(), the context argument should be interpreted safely, i.e., if context is not a string (empty list etc.), converting it to string might result in something like "[]", which is non-empty and leads to unintended memory context fetch. So here we should ensure the context value used is string; if not string or empty, treat as empty string.

Hence, two parts of the code should be changed:

1. In Agent.execute_task(), add validation for context to treat non-string, non-None values like empty list as no context.

2. In ContextualMemory.build_context_for_task(), ensure context is a string or empty string before usage.

Patch:

# modification 1
```
<file>src/crewai/agent.py</file>
<original>        if context:
            task_prompt = self.i18n.slice("task_with_context").format(
                task=task_prompt, context=context
            )</original>
<patched>        if context and isinstance(context, str):
            task_prompt = self.i18n.slice("task_with_context").format(
                task=task_prompt, context=context
            )</patched>
```

# modification 2
```
<file>src/crewai/memory/contextual/contextual_memory.py</file>
<original>32     def build_context_for_task(self, task, context) -> str:
33         """
34         Automatically builds a minimal, highly relevant set of contextual information
35         for a given task.
36         """
37         query = f"{task.description} {context}".strip()
38 
39         if query == "":
40             return ""
41 
42         context = []
43         context.append(self._fetch_ltm_context(task.description))
44         context.append(self._fetch_stm_context(query))
45         context.append(self._fetch_entity_context(query))
46         context.append(self._fetch_external_context(query))
47         if self.memory_provider == "mem0":
48             context.append(self._fetch_user_context(query))
49         return "\n".join(filter(None, context))</original>
<patched>32     def build_context_for_task(self, task, context) -> str:
33         """
34         Automatically builds a minimal, highly relevant set of contextual information
35         for a given task.
36         """
37         # Ensure context is string, otherwise treat as empty
38         if not isinstance(context, str):
39             context_str = ""
40         else:
41             context_str = context
42 
43         query = f"{task.description} {context_str}".strip()
44 
45         if query == "":
46             return ""
47 
48         context_accum = []
49         context_accum.append(self._fetch_ltm_context(task.description))
50         context_accum.append(self._fetch_stm_context(query))
51         context_accum.append(self._fetch_entity_context(query))
52         context_accum.append(self._fetch_external_context(query))
53         if self.memory_provider == "mem0":
54             context_accum.append(self._fetch_user_context(query))
55         return "\n".join(filter(None, context_accum))</patched>
```

Explanation:
- In execute_task, the original check on `context` is changed from `if context:` to `if context and isinstance(context, str):` to ensure context is a non-empty string. This avoids the case where context=[] (empty list) passes the check and gets used as context string.

- In build_context_for_task, the context argument is checked if it is a string, otherwise replaced with empty string. This prevents creating a query string with the string representation of non-string context like empty list "[]". Then use this safe string for memory fetching calls.

These minimal changes preserve existing functionality when context is passed properly as a string or None, while preventing unintended context propagation when context is empty list or other falsy non-string objects.