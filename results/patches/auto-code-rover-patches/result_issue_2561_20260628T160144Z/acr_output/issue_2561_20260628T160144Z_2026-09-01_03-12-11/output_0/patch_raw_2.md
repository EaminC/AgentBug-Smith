The reasoning:

The issue requests that the `tool` decorator supports the `result_as_answer` parameter to be passed when decorating a function, similar to how the full `Tool` class supports it. Currently, the `tool` decorator does not accept this parameter, and it would be good to add it optionally as a keyword-only argument. This means updating the `tool` function signature to accept `result_as_answer: bool = False` as an optional argument.

Inside the decorator, when creating the `Tool` instance, the `result_as_answer` parameter should be passed along.

Since the existing API allows two styles of usage:

- `@tool` (no argument) with the decorated function

- `@tool("name")` with a name string

We'll extend it to accept the keyword argument `result_as_answer` in addition. The simplest is to redesign the outer `tool` function to accept `*args` and keyword args `**kwargs` and pick out `result_as_answer` from kwargs with a default.

That way, existing calls remain compatible, and the new parameter works.

Hence, the change is:

- Add `result_as_answer=False` parameter to `tool`.

- Pass it into the `Tool` constructor.

No other changes are required.

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
<patched>247 def tool(*args, result_as_answer: bool = False):
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