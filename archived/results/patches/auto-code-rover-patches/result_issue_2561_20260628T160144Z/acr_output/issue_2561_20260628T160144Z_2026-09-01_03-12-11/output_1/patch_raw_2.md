The reasoning:

The issue requests extending the `@tool` decorator to accept a `result_as_answer` parameter so that decorated functions can specify this flag conveniently, rather than having to create a full class. Examining the `tool` decorator implementation, it currently accepts only positional arguments (either a function or a string tool name), but no options like `result_as_answer`.

To enable this, the `tool` decorator should accept keyword arguments, including `result_as_answer`. Then, when creating the `Tool` instance (the actual return of the decorator), the `result_as_answer` value should be passed along.

This requires:

- Updating `tool` to accept `*args, **kwargs`.
- Extracting the `result_as_answer` keyword argument with a default value (probably False).
- Passing it to the `Tool` constructor.

No other changes are needed since the `Tool` class already supports a `result_as_answer` argument based on the context.

Here is the patch to implement this cleanly.

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
251     result_as_answer = kwargs.pop("result_as_answer", False)
252 
253     def _make_with_name(tool_name: str) -> Callable:
254         def _make_tool(f: Callable) -> BaseTool:
255             if f.__doc__ is None:
256                 raise ValueError("Function must have a docstring")
257             if f.__annotations__ is None:
258                 raise ValueError("Function must have type annotations")
259 
260             class_name = "".join(tool_name.split()).title()
261             args_schema = type(
262                 class_name,
263                 (PydanticBaseModel,),
264                 {
265                     "__annotations__": {
266                         k: v for k, v in f.__annotations__.items() if k != "return"
267                     },
268                 },
269             )
270 
271             return Tool(
272                 name=tool_name,
273                 description=f.__doc__,
274                 func=f,
275                 args_schema=args_schema,
276                 result_as_answer=result_as_answer,
277             )
278 
279         return _make_tool
280 
281     if len(args) == 1 and callable(args[0]):
282         return _make_with_name(args[0].__name__)(args[0])
283     if len(args) == 1 and isinstance(args[0], str):
284         return _make_with_name(args[0])
285     raise ValueError("Invalid arguments")
</patched>
```