```
<file>src/strands/tools/registry.py</file>
<original>229     def register_tool(self, tool: AgentTool) -> None:
230         """Register a tool function with the given name.
231 
232         Args:
233             tool: The tool to register.
234         """
235         logger.debug(
236             "tool_name=<%s>, tool_type=<%s>, is_dynamic=<%s> | registering tool",
237             tool.tool_name,
238             tool.tool_type,
239             tool.is_dynamic,
240         )
241 
242         # Check duplicate tool name, throw on duplicate tool names except if hot_reloading is enabled
243         if tool.tool_name in self.registry and not tool.supports_hot_reload:
244             raise ValueError(
245                 f"Tool name '{tool.tool_name}' already exists. Cannot register tools with exact same name."
246             )
247 
248         # Check for normalized name conflicts (- vs _)
249         if self.registry.get(tool.tool_name) is None:
250             normalized_name = tool.tool_name.replace("-", "_")
251 
252             matching_tools = [
253                 tool_name
254                 for (tool_name, tool) in self.registry.items()
255                 if tool_name.replace("-", "_") == normalized_name
256             ]
257 
258             if matching_tools:
259                 raise ValueError(
260                     f"Tool name '{tool.tool_name}' already exists as '{matching_tools[0]}'."
261                     " Cannot add a duplicate tool which differs by a '-' or '_'"
262                 )
263 
264         # Register in main registry
265         self.registry[tool.tool_name] = tool
266 
267         # Register in dynamic tools if applicable
268         if tool.is_dynamic:
269             self.dynamic_tools[tool.tool_name] = tool
270 
271             if not tool.supports_hot_reload:
272                 logger.debug("tool_name=<%s>, tool_type=<%s> | skipping hot reloading", tool.tool_name, tool.tool_type)
273                 return
274 
275             logger.debug(
276                 "tool_name=<%s>, tool_registry=<%s>, dynamic_tools=<%s> | tool registered",
277                 tool.tool_name,
278                 list(self.registry.keys()),
279                 list(self.dynamic_tools.keys()),
280             )
281 </original>
<patched>229     def register_tool(self, tool: AgentTool) -> None:
230         """Register a tool function with the given name.
231 
232         Args:
233             tool: The tool to register.
234         """
235         logger.debug(
236             "tool_name=<%s>, tool_type=<%s>, is_dynamic=<%s> | registering tool",
237             tool.tool_name,
238             tool.tool_type,
239             tool.is_dynamic,
240         )
241 
242         # Check duplicate tool name, throw on duplicate tool names except if hot_reloading is enabled
243         if tool.tool_name in self.registry and not tool.supports_hot_reload:
244             raise ValueError(
245                 f"Tool name '{tool.tool_name}' already exists. Cannot register tools with exact same name."
246             )
247 
248         # Check for normalized name conflicts (- vs _)
249         if self.registry.get(tool.tool_name) is None:
250             normalized_name = tool.tool_name.replace("-", "_")
251 
252             matching_tools = [
253                 tool_name
254                 for (tool_name, t) in self.registry.items()
255                 if tool_name.replace("-", "_") == normalized_name
256             ]
257 
258             if matching_tools:
259                 raise ValueError(
260                     f"Tool name '{tool.tool_name}' already exists as '{matching_tools[0]}'."
261                     " Cannot add a duplicate tool which differs by a '-' or '_'"
262                 )
263 
264         # Register in main registry atomically
265         # For atomic swap, replace reference in one step
266         self.registry[tool.tool_name] = tool
267 
268         # Register in dynamic tools if applicable
269         if tool.is_dynamic:
270             self.dynamic_tools[tool.tool_name] = tool
271 
272             if not tool.supports_hot_reload:
273                 logger.debug("tool_name=<%s>, tool_type=<%s> | skipping hot reloading", tool.tool_name, tool.tool_type)
274                 return
275 
276             logger.debug(
277                 "tool_name=<%s>, tool_registry=<%s>, dynamic_tools=<%s> | tool registered",
278                 tool.tool_name,
279                 list(self.registry.keys()),
280                 list(self.dynamic_tools.keys()),
281             )
</patched>
</file>

<file>src/strands/tools/registry.py</file>
<original>327     def reload_tool(self, tool_name: str) -> None:
328         """Reload a specific tool module.
329 
330         Args:
331             tool_name: Name of the tool to reload.
332 
333         Raises:
334             FileNotFoundError: If the tool file cannot be found.
335             ImportError: If there are issues importing the tool module.
336             ValueError: If the tool specification is invalid or required components are missing.
337             Exception: For other errors during tool reloading.
338         """
339         try:
340             # Check for tool file
341             logger.debug("tool_name=<%s> | searching directories for tool", tool_name)
342             tools_dirs = self.get_tools_dirs()
343             tool_path = None
344 
345             # Search for the tool file in all tool directories
346             for tools_dir in tools_dirs:
347                 temp_path = tools_dir / f"{tool_name}.py"
348                 if temp_path.exists():
349                     tool_path = temp_path
350                     break
351 
352             if not tool_path:
353                 raise FileNotFoundError(f"No tool file found for: {tool_name}")
354 
355             logger.debug("tool_name=<%s> | reloading tool", tool_name)
356 
357             # Add tool directory to path temporarily
358             tool_dir = str(tool_path.parent)
359             sys.path.insert(0, tool_dir)
360             try:
361                 # Load the module directly using spec
362                 spec = util.spec_from_file_location(tool_name, str(tool_path))
363                 if spec is None:
364                     raise ImportError(f"Could not load spec for {tool_name}")
365 
366                 module = util.module_from_spec(spec)
367                 sys.modules[tool_name] = module
368 
369                 if spec.loader is None:
370                     raise ImportError(f"Could not load {tool_name}")
371 
372                 spec.loader.exec_module(module)
373 
374             finally:
375                 # Remove the temporary path
376                 sys.path.remove(tool_dir)
377 
378             # Look for function-based tools first
379             try:
380                 function_tools = self._scan_module_for_tools(module)
381 
382                 if function_tools:
383                     for function_tool in function_tools:
384                         # Register the function-based tool
385                         self.register_tool(function_tool)
386 
387                         # Update tool configuration if available
388                         if self.tool_config is not None:
389                             self._update_tool_config(self.tool_config, {"spec": function_tool.tool_spec})
390 
391                     logger.debug("tool_name=<%s> | successfully reloaded function-based tool from module", tool_name)
392                     return
393             except ImportError:
394                 logger.debug("function tool loader not available | falling back to traditional tools")
395 
396             # Fall back to traditional module-level tools
397             if not hasattr(module, "TOOL_SPEC"):
398                 raise ValueError(
399                     f"Tool {tool_name} is missing TOOL_SPEC (neither at module level nor as a decorated function)"
400                 )
401 
402             expected_func_name = tool_name
403             if not hasattr(module, expected_func_name):
404                 raise ValueError(f"Tool {tool_name} is missing {expected_func_name} function")
405 
406             tool_function = getattr(module, expected_func_name)
407             if not callable(tool_function):
408                 raise ValueError(f"Tool {tool_name} function is not callable")
409 
410             # Validate tool spec
411             self.validate_tool_spec(module.TOOL_SPEC)
412 
413             new_tool = PythonAgentTool(tool_name, module.TOOL_SPEC, tool_function)
414 
415             # Register the tool
416             self.register_tool(new_tool)
417 
418             # Update tool configuration if available
419             if self.tool_config is not None:
420                 self._update_tool_config(self.tool_config, {"spec": module.TOOL_SPEC})
421             logger.debug("tool_name=<%s> | successfully reloaded tool", tool_name)
422 
423         except Exception:
424             logger.exception("tool_name=<%s> | failed to reload tool", tool_name)
425             raise
426 </original>
<patched>327     def reload_tool(self, tool_name: str) -> None:
328         """Reload a specific tool module.
329 
330         Args:
331             tool_name: Name of the tool to reload.
332 
333         Raises:
334             FileNotFoundError: If the tool file cannot be found.
335             ImportError: If there are issues importing the tool module.
336             ValueError: If the tool specification is invalid or required components are missing.
337             Exception: For other errors during tool reloading.
338         """
339         try:
340             # Check for tool file
341             logger.debug("tool_name=<%s> | searching directories for tool", tool_name)
342             tools_dirs = self.get_tools_dirs()
343             tool_path = None
344 
345             # Search for the tool file in all tool directories
346             for tools_dir in tools_dirs:
347                 temp_path = tools_dir / f"{tool_name}.py"
348                 if temp_path.exists():
349                     tool_path = temp_path
350                     break
351 
352             if not tool_path:
353                 raise FileNotFoundError(f"No tool file found for: {tool_name}")
354 
355             logger.debug("tool_name=<%s> | reloading tool", tool_name)
356 
357             # Add tool directory to path temporarily
358             tool_dir = str(tool_path.parent)
359             sys.path.insert(0, tool_dir)
360             try:
361                 # Load the module directly using spec
362                 spec = util.spec_from_file_location(tool_name, str(tool_path))
363                 if spec is None:
364                     raise ImportError(f"Could not load spec for {tool_name}")
365 
366                 module = util.module_from_spec(spec)
367                 sys.modules[tool_name] = module
368 
369                 if spec.loader is None:
370                     raise ImportError(f"Could not load {tool_name}")
371 
372                 spec.loader.exec_module(module)
373 
374             finally:
375                 # Remove the temporary path
376                 sys.path.remove(tool_dir)
377 
378             # Look for function-based tools first
379             try:
380                 function_tools = self._scan_module_for_tools(module)
381 
382                 if function_tools:
383                     for function_tool in function_tools:
384                         # Register the function-based tool
385                         # Register tool atomically with support for swapping
386                         self.register_tool(function_tool)
387 
388                         # Update tool configuration if available
389                         if self.tool_config is not None:
390                             self._update_tool_config(self.tool_config, {"spec": function_tool.tool_spec})
391 
392                     logger.debug("tool_name=<%s> | successfully reloaded function-based tool from module", tool_name)
393                     return
394             except ImportError:
395                 logger.debug("function tool loader not available | falling back to traditional tools")
396 
397             # Fall back to traditional module-level tools
398             if not hasattr(module, "TOOL_SPEC"):
399                 raise ValueError(
400                     f"Tool {tool_name} is missing TOOL_SPEC (neither at module level nor as a decorated function)"
401                 )
402 
403             expected_func_name = tool_name
404             if not hasattr(module, expected_func_name):
405                 raise ValueError(f"Tool {tool_name} is missing {expected_func_name} function")
406 
407             tool_function = getattr(module, expected_func_name)
408             if not callable(tool_function):
409                 raise ValueError(f"Tool {tool_name} function is not callable")
410 
411             # Validate tool spec
412             self.validate_tool_spec(module.TOOL_SPEC)
413 
414             new_tool = PythonAgentTool(tool_name, module.TOOL_SPEC, tool_function)
415 
416             # Register the tool atomically
417             self.register_tool(new_tool)
418 
419             # Update tool configuration if available
420             if self.tool_config is not None:
421                 self._update_tool_config(self.tool_config, {"spec": module.TOOL_SPEC})
422             logger.debug("tool_name=<%s> | successfully reloaded tool", tool_name)
423 
424         except Exception:
425             logger.exception("tool_name=<%s> | failed to reload tool", tool_name)
426             raise
426 </patched>
</file>