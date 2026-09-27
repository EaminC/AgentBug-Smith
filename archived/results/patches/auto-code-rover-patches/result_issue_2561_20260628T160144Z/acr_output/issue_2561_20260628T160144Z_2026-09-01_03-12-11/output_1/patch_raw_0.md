The reasoning:
The current `tool` decorator does not accept any parameters except the function or a string for the name. To support the new feature where `result_as_answer` can be set at decorator time, the decorator needs to accept an optional keyword argument `result_as_answer` with a default value (probably True, inferred from the Tool default). This flag needs to be passed to the `Tool` constructor when a decorated function is converted.

The minimal approach:
- Modify the `tool` decorator to accept a keyword argument `result_as_answer=True`.
- Pass this flag to the `Tool` constructor.
- Since the decorator currently recognizes either a single callable or a single string and then returns a callable, we need to modify the signature to accept `*args, result_as_answer=True` or `**kwargs` for backward compatibility.
- We must also update the `_make_with_name` function signature because it will close over `result_as_answer`.
- This allows the syntax `@tool("name", result_as_answer=False)`.

No other code changes appear necessary.

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
<patched>247 def tool(*args, result_as_answer=True):
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