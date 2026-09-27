# Reasoning

The feature request is to support a new parameter `result_as_answer` for the `@tool` decorator, allowing tool functions decorated with `@tool` to specify whether their result should be treated as the answer.

To achieve this, we need two main changes:

1. Add a `result_as_answer` attribute to the `Tool` class so it can keep track of this setting.
   - It should be a boolean with a default value (`False` would be sensible).
   - This keeps backward compatibility with existing tools.

2. Modify the `tool` decorator to accept an optional `result_as_answer` argument.
   - The decorator currently only accepts a name or a callable.
   - We will update it to accept an optional `result_as_answer` keyword argument and pass that along when constructing the `Tool` instance.
   - This must be done while maintaining backward compatibility in existing usage patterns.

No other code or files need changing because the core mechanism and usage seem already in place for defining tools as functions.

---

# Patch

```
<file>src/crewai/tools/base_tool.py</file>
<original>180 class Tool(BaseTool):
181     """The function that will be executed when the tool is called."""
182 
183     func: Callable
184 
185     def _run(self, *args: Any, **kwargs: Any) -> Any:
186         return self.func(*args, **kwargs)
187 
188     @classmethod
189     def from_langchain(cls, tool: Any) -> "Tool":
190         """Create a Tool instance from a CrewStructuredTool.
191 
192         This method takes a CrewStructuredTool object and converts it into a
193         Tool instance. It ensures that the provided tool has a callable 'func'
194         attribute and infers the argument schema if not explicitly provided.
195 
196         Args:
197             tool (Any): The CrewStructuredTool object to be converted.
198 
199         Returns:
200             Tool: A new Tool instance created from the provided CrewStructuredTool.
201 
202         Raises:
203             ValueError: If the provided tool does not have a callable 'func' attribute.
204         """
205         if not hasattr(tool, "func") or not callable(tool.func):
206             raise ValueError("The provided tool must have a callable 'func' attribute.")
207 
208         args_schema = getattr(tool, "args_schema", None)
209 
210         if args_schema is None:
211             # Infer args_schema from the function signature if not provided
212             func_signature = signature(tool.func)
213             annotations = func_signature.parameters
214             args_fields = {}
215             for name, param in annotations.items():
216                 if name != "self":
217                     param_annotation = (
218                         param.annotation if param.annotation != param.empty else Any
219                     )
220                     field_info = Field(
221                         default=...,
222                         description="",
223                     )
224                     args_fields[name] = (param_annotation, field_info)
225             if args_fields:
226                 args_schema = create_model(f"{tool.name}Input", **args_fields)
227             else:
228                 # Create a default schema with no fields if no parameters are found
229                 args_schema = create_model(
230                     f"{tool.name}Input", __base__=PydanticBaseModel
231                 )
232 
233         return cls(
234             name=getattr(tool, "name", "Unnamed Tool"),
235             description=getattr(tool, "description", ""),
236             func=tool.func,
237             args_schema=args_schema,
238         )
</original>
<patched>180 class Tool(BaseTool):
181     """The function that will be executed when the tool is called."""
182 
183     func: Callable
184 
185     result_as_answer: bool = False
186 
187     def _run(self, *args: Any, **kwargs: Any) -> Any:
188         return self.func(*args, **kwargs)
189 
190     @classmethod
191     def from_langchain(cls, tool: Any) -> "Tool":
192         """Create a Tool instance from a CrewStructuredTool.
193 
194         This method takes a CrewStructuredTool object and converts it into a
195         Tool instance. It ensures that the provided tool has a callable 'func'
196         attribute and infers the argument schema if not explicitly provided.
197 
198         Args:
199             tool (Any): The CrewStructuredTool object to be converted.
200 
201         Returns:
202             Tool: A new Tool instance created from the provided CrewStructuredTool.
203 
204         Raises:
205             ValueError: If the provided tool does not have a callable 'func' attribute.
206         """
207         if not hasattr(tool, "func") or not callable(tool.func):
208             raise ValueError("The provided tool must have a callable 'func' attribute.")
209 
210         args_schema = getattr(tool, "args_schema", None)
211 
212         if args_schema is None:
213             # Infer args_schema from the function signature if not provided
214             func_signature = signature(tool.func)
215             annotations = func_signature.parameters
216             args_fields = {}
217             for name, param in annotations.items():
218                 if name != "self":
219                     param_annotation = (
220                         param.annotation if param.annotation != param.empty else Any
221                     )
222                     field_info = Field(
223                         default=...,
224                         description="",
225                     )
226                     args_fields[name] = (param_annotation, field_info)
227             if args_fields:
228                 args_schema = create_model(f"{tool.name}Input", **args_fields)
229             else:
230                 # Create a default schema with no fields if no parameters are found
231                 args_schema = create_model(
232                     f"{tool.name}Input", __base__=PydanticBaseModel
233                 )
234 
235         return cls(
236             name=getattr(tool, "name", "Unnamed Tool"),
237             description=getattr(tool, "description", ""),
238             func=tool.func,
239             args_schema=args_schema,
240             result_as_answer=getattr(tool, "result_as_answer", False),
241         )
</patched>
```

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