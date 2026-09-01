The main changes needed are:  
1. Add a `result_as_answer` boolean attribute to the `Tool` class, with a default value (e.g., False). This attribute will store whether the tool's result should be treated as an answer.  
2. Modify the `tool` decorator to accept an optional `result_as_answer` argument and pass that to the `Tool` instance during creation. This argument should default to False if not provided to maintain backward compatibility.  
3. Ensure existing behavior of auto-generating schema and name remains unchanged.  

This way, users can write:  
```python
@tool("example_tool", result_as_answer=True)
def some_func(...):
    ...
```
and that parameter will be passed onto the created `Tool` instance.

---

# modification 1  
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
184     result_as_answer: bool = False
185 
186     def _run(self, *args: Any, **kwargs: Any) -> Any:
187         return self.func(*args, **kwargs)
188 
189     @classmethod
190     def from_langchain(cls, tool: Any) -> "Tool":
191         """Create a Tool instance from a CrewStructuredTool.
192 
193         This method takes a CrewStructuredTool object and converts it into a
194         Tool instance. It ensures that the provided tool has a callable 'func'
195         attribute and infers the argument schema if not explicitly provided.
196 
197         Args:
198             tool (Any): The CrewStructuredTool object to be converted.
199 
200         Returns:
201             Tool: A new Tool instance created from the provided CrewStructuredTool.
202 
203         Raises:
204             ValueError: If the provided tool does not have a callable 'func' attribute.
205         """
206         if not hasattr(tool, "func") or not callable(tool.func):
207             raise ValueError("The provided tool must have a callable 'func' attribute.")
208 
209         args_schema = getattr(tool, "args_schema", None)
210 
211         if args_schema is None:
212             # Infer args_schema from the function signature if not provided
213             func_signature = signature(tool.func)
214             annotations = func_signature.parameters
215             args_fields = {}
216             for name, param in annotations.items():
217                 if name != "self":
218                     param_annotation = (
219                         param.annotation if param.annotation != param.empty else Any
220                     )
221                     field_info = Field(
222                         default=...,
223                         description="",
224                     )
225                     args_fields[name] = (param_annotation, field_info)
226             if args_fields:
227                 args_schema = create_model(f"{tool.name}Input", **args_fields)
228             else:
229                 # Create a default schema with no fields if no parameters are found
230                 args_schema = create_model(
231                     f"{tool.name}Input", __base__=PydanticBaseModel
232                 )
233 
234         return cls(
235             name=getattr(tool, "name", "Unnamed Tool"),
236             description=getattr(tool, "description", ""),
237             func=tool.func,
238             args_schema=args_schema,
239             result_as_answer=getattr(tool, "result_as_answer", False),
240         )
</patched>
```

# modification 2  
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
283     raise ValueError("Invalid arguments")</original>
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