The reasoning:
To allow the `tool` decorator to accept a `result_as_answer` parameter, we need to make the decorator able to accept keyword arguments. Currently, the `tool` decorator only accepts either a single callable or a single string argument.

To support this, we should check if the first argument is a string (the tool name) and allow keyword arguments like `result_as_answer`. Then, when the inner `_make_tool` function creates the `Tool` instance, it should pass along the `result_as_answer` argument (or default to False if not provided).

Importantly, default behavior and backward compatibility should be preserved: if the decorator is used without arguments `@tool` or with only a name `@tool("name")`, it should work exactly as before.

This requires:
- Changing `tool` to accept `*args, **kwargs`.
- Extracting `result_as_answer` with a default value.
- Passing this flag down to the `Tool` constructor inside `_make_tool`.

This approach minimally impacts the existing code but adds the requested feature.

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
252     result_as_answer = kwargs.pop("result_as_answer", False)
253 
254     def _make_with_name(tool_name: str) -> Callable:
255         def _make_tool(f: Callable) -> BaseTool:
256             if f.__doc__ is None:
257                 raise ValueError("Function must have a docstring")
258             if f.__annotations__ is None:
259                 raise ValueError("Function must have type annotations")
260 
261             class_name = "".join(tool_name.split()).title()
262             args_schema = type(
263                 class_name,
264                 (PydanticBaseModel,),
265                 {
266                     "__annotations__": {
267                         k: v for k, v in f.__annotations__.items() if k != "return"
268                     },
269                 },
270             )
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