Reasoning:
The issue requests allowing the @tool decorator to accept a `result_as_answer` parameter and pass it to the underlying Tool instance. Currently, the decorator only accepts a `name` (string) or a bare function. We should enhance the decorator to accept an optional boolean keyword argument `result_as_answer` with a default value (probably True, or False if that is default in Tool) and pass it when creating the Tool object.

The main structural change will be:
- Update the signature of `tool` to accept `*args, result_as_answer=True` or `False` (depending on what the default should be).
- Propagate `result_as_answer` to the `_make_with_name` function, adding it as a parameter.
- Use this parameter when constructing the Tool instance (i.e., pass `result_as_answer=result_as_answer`).

No other behavioral changes are needed. The code should still support the two existing call styles:
- `@tool` applied directly to a function (with the function name as tool name),
- `@tool("name")` returning a decorator that creates a Tool with that name.

We just add support for an optional keyword argument: `@tool("name", result_as_answer=False)`.

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
<patched>247 def tool(*args, result_as_answer: bool = True):
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
275                 result_as_answer=result_as_answer,
276             )
277 
278         return _make_tool
279 
280     if len(args) == 1 and callable(args[0]):
281         return _make_with_name(args[0].__name__)(args[0])
282     if len(args) == 1 and isinstance(args[0], str):
283         return _make_with_name(args[0])
284     raise ValueError("Invalid arguments")
</patched>
```