Reasoning:
The issue is to allow the `@tool` decorator to accept an optional parameter `result_as_answer`. Currently, the `tool` function only accepts a single argument (either a callable or a string for the tool name), but not any keyword arguments. We want to enable a signature like `@tool(name, result_as_answer=False)`. To do this, we will:

- Update the `tool` function signature to accept `*args` and `**kwargs`.
- Extract and handle the `result_as_answer` keyword argument inside `_make_tool`.
- Pass this `result_as_answer` parameter to the `Tool` constructor, preserving existing behavior by defaulting to `None` or `False` (depending on the base class implementation).
- Keep backward compatibility, so if no `result_as_answer` is provided, it behaves as before.

This requires updating the decorator factory and also `_make_tool` inner function.

---

Patch:

```
<file>src/crewai/tools/base_tool.py</file>
<original>247 def tool(*args):
248     """
249     Decorator to create a tool from a function.
250     """
251 
252     def _make_with_name(tool_name: str) -> Callable:
253         def _make_tool(f: Callable) -> BaseTool:
254             if f.__doc__ is None:
255                 raise ValueError("Function must have a docstring")
256             if f.__annotations__ is None:
257                 raise ValueError("Function must have type annotations")
258 
259             class_name = "".join(tool_name.split()).title()
260             args_schema = type(
261                 class_name,
262                 (PydanticBaseModel,),
263                 {
264                     "__annotations__": {
265                         k: v for k, v in f.__annotations__.items() if k != "return"
266                     },
267                 },
268             )
269 
270             return Tool(
271                 name=tool_name,
272                 description=f.__doc__,
273                 func=f,
274                 args_schema=args_schema,
275             )
276 
277         return _make_tool
278 
279     if len(args) == 1 and callable(args[0]):
280         return _make_with_name(args[0].__name__)(args[0])
281     if len(args) == 1 and isinstance(args[0], str):
282         return _make_with_name(args[0])
283     raise ValueError("Invalid arguments")
</original>
<patched>247 def tool(*args, **kwargs):
248     """
249     Decorator to create a tool from a function.
250     """
251 
252     def _make_with_name(tool_name: str) -> Callable:
253         def _make_tool(f: Callable) -> BaseTool:
254             if f.__doc__ is None:
255                 raise ValueError("Function must have a docstring")
256             if f.__annotations__ is None:
257                 raise ValueError("Function must have type annotations")
258 
259             class_name = "".join(tool_name.split()).title()
260             args_schema = type(
261                 class_name,
262                 (PydanticBaseModel,),
263                 {
264                     "__annotations__": {
265                         k: v for k, v in f.__annotations__.items() if k != "return"
266                     },
267                 },
268             )
269 
270             result_as_answer = kwargs.get("result_as_answer", None)
271 
272             return Tool(
273                 name=tool_name,
274                 description=f.__doc__,
275                 func=f,
276                 args_schema=args_schema,
277                 result_as_answer=result_as_answer,
278             )
279 
280         return _make_tool
281 
282     if len(args) == 1 and callable(args[0]):
283         return _make_with_name(args[0].__name__)(args[0])
284     if len(args) == 1 and isinstance(args[0], str):
285         return _make_with_name(args[0])
286     raise ValueError("Invalid arguments")
</patched>
```
