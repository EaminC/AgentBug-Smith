The issue arises because, from Pydantic v2.12 onwards, models that include types such as `typing.Literal` or other complex annotations require explicit rebuilding with `model_rebuild()` after dynamic creation via `create_model()`. Without calling `model_rebuild()`, the model is notionally incomplete and will raise errors like the one described.

The code in `_create_input_model` dynamically constructs a Pydantic model from function parameters but currently does not call `model_rebuild()` on the created model. To fix this, after the model is created we should call `model_rebuild()`.

Since not all pydantic versions require this (only versions after 2.11), we should detect the Pydantic version at runtime and conditionally apply `model_rebuild()` if needed.

This will maintain backward compatibility with older Pydantic versions while supporting newer ones.

---

```
<file>src/strands/tools/decorator.py</file>
<original>187     def _create_input_model(self) -> Type[BaseModel]:
188         """Create a Pydantic model from function signature for input validation.
189 
190         This method analyzes the function's signature, type hints, and docstring to create a Pydantic model that can
191         validate input data before passing it to the function.
192 
193         Special parameters that can be automatically injected are excluded from the model.
194 
195         Returns:
196             A Pydantic BaseModel class customized for the function's parameters.
197         """
198         field_definitions: dict[str, Any] = {}
199 
200         for name, param in self.signature.parameters.items():
201             # Skip parameters that will be automatically injected
202             if self._is_special_parameter(name):
203                 continue
204 
205             # Use param.annotation directly to get the raw type hint. Using get_type_hints()
206             # can cause inconsistent behavior across Python versions for complex Annotated types.
207             param_type = param.annotation
208             if param_type is inspect.Parameter.empty:
209                 param_type = Any
210             default = ... if param.default is inspect.Parameter.empty else param.default
211 
212             actual_type, field_info = self._extract_annotated_metadata(param_type, name, default)
213             field_definitions[name] = (actual_type, field_info)
214 
215         model_name = f"{self.func.__name__.capitalize()}Tool"
216 
217         if field_definitions:
218             return create_model(model_name, **field_definitions)
219         else:
220             return create_model(model_name)
</original>
<patched>187     def _create_input_model(self) -> Type[BaseModel]:
188         """Create a Pydantic model from function signature for input validation.
189 
190         This method analyzes the function's signature, type hints, and docstring to create a Pydantic model that can
191         validate input data before passing it to the function.
192 
193         Special parameters that can be automatically injected are excluded from the model.
194 
195         Returns:
196             A Pydantic BaseModel class customized for the function's parameters.
197         """
198         from pydantic import __version__ as pydantic_version  # Import here to avoid top-level import
199         from packaging.version import Version
200 
201         field_definitions: dict[str, Any] = {}
202 
203         for name, param in self.signature.parameters.items():
204             # Skip parameters that will be automatically injected
205             if self._is_special_parameter(name):
206                 continue
207 
208             # Use param.annotation directly to get the raw type hint. Using get_type_hints()
209             # can cause inconsistent behavior across Python versions for complex Annotated types.
210             param_type = param.annotation
211             if param_type is inspect.Parameter.empty:
212                 param_type = Any
213             default = ... if param.default is inspect.Parameter.empty else param.default
214 
215             actual_type, field_info = self._extract_annotated_metadata(param_type, name, default)
216             field_definitions[name] = (actual_type, field_info)
217 
218         model_name = f"{self.func.__name__.capitalize()}Tool"
219 
220         if field_definitions:
221             model = create_model(model_name, **field_definitions)
222         else:
223             model = create_model(model_name)
224 
225         # Call model_rebuild() if pydantic version > 2.11 to support newer typing features
226         if Version(pydantic_version) > Version("2.11"):
227             model.model_rebuild()
228 
229         return model
</patched>
```
