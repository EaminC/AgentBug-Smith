```
<file>src/strands/tools/registry.py</file>
<original>    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool function with the given name.

        Args:
            tool: The tool to register.
        """
        logger.debug(
            "tool_name=<%s>, tool_type=<%s>, is_dynamic=<%s> | registering tool",
            tool.tool_name,
            tool.tool_type,
            tool.is_dynamic,
        )

        # Check duplicate tool name, throw on duplicate tool names except if hot_reloading is enabled
        if tool.tool_name in self.registry and not tool.supports_hot_reload:
            raise ValueError(
                f"Tool name '{tool.tool_name}' already exists. Cannot register tools with exact same name."
            )

        # Check for normalized name conflicts (- vs _)
        if self.registry.get(tool.tool_name) is None:
            normalized_name = tool.tool_name.replace("-", "_")

            matching_tools = [
                tool_name
                for (tool_name, tool) in self.registry.items()
                if tool_name.replace("-", "_") == normalized_name
            ]

            if matching_tools:
                raise ValueError(
                    f"Tool name '{tool.tool_name}' already exists as '{matching_tools[0]}'."
                    " Cannot add a duplicate tool which differs by a '-' or '_'"
                )

        # Register in main registry
        self.registry[tool.tool_name] = tool

        # Register in dynamic tools if applicable
        if tool.is_dynamic:
            self.dynamic_tools[tool.tool_name] = tool

            if not tool.supports_hot_reload:
                logger.debug("tool_name=<%s>, tool_type=<%s> | skipping hot reloading", tool.tool_name, tool.tool_type)
                return

            logger.debug(
                "tool_name=<%s>, tool_registry=<%s>, dynamic_tools=<%s> | tool registered",
                tool.tool_name,
                list(self.registry.keys()),
                list(self.dynamic_tools.keys()),
            )</original>
<patched>    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool function with the given name.

        Args:
            tool: The tool to register.
        """
        logger.debug(
            "tool_name=<%s>, tool_type=<%s>, is_dynamic=<%s> | registering tool",
            tool.tool_name,
            tool.tool_type,
            tool.is_dynamic,
        )

        # Check duplicate tool name, except allow hot reloading
        if tool.tool_name in self.registry:
            if not tool.supports_hot_reload:
                raise ValueError(
                    f"Tool name '{tool.tool_name}' already exists. Cannot register tools with exact same name."
                )
            else:
                # atomically swap tool references in registry and dynamic_tools for hot reload support
                self.registry[tool.tool_name] = tool
                if tool.is_dynamic:
                    self.dynamic_tools[tool.tool_name] = tool
                logger.debug("tool_name=<%s> | hot-reloaded tool registered", tool.tool_name)
                return

        # Check for normalized name conflicts (- vs _)
        if self.registry.get(tool.tool_name) is None:
            normalized_name = tool.tool_name.replace("-", "_")

            matching_tools = [
                tool_name
                for (tool_name, tool) in self.registry.items()
                if tool_name.replace("-", "_") == normalized_name
            ]

            if matching_tools:
                raise ValueError(
                    f"Tool name '{tool.tool_name}' already exists as '{matching_tools[0]}'."
                    " Cannot add a duplicate tool which differs by a '-' or '_'"
                )

        # Register in main registry
        self.registry[tool.tool_name] = tool

        # Register in dynamic tools if applicable
        if tool.is_dynamic:
            self.dynamic_tools[tool.tool_name] = tool

            if not tool.supports_hot_reload:
                logger.debug("tool_name=<%s>, tool_type=<%s> | skipping hot reloading", tool.tool_name, tool.tool_type)
                return

            logger.debug(
                "tool_name=<%s>, tool_registry=<%s>, dynamic_tools=<%s> | tool registered",
                tool.tool_name,
                list(self.registry.keys()),
                list(self.dynamic_tools.keys()),
            )</patched>
```

```
<file>src/strands/tools/registry.py</file>
<original>    def reload_tool(self, tool_name: str) -> None:
        """Reload a specific tool module.

        Args:
            tool_name: Name of the tool to reload.

        Raises:
            FileNotFoundError: If the tool file cannot be found.
            ImportError: If there are issues importing the tool module.
            ValueError: If the tool specification is invalid or required components are missing.
            Exception: For other errors during tool reloading.
        """
        try:
            # Check for tool file
            logger.debug("tool_name=<%s> | searching directories for tool", tool_name)
            tools_dirs = self.get_tools_dirs()
            tool_path = None

            # Search for the tool file in all tool directories
            for tools_dir in tools_dirs:
                temp_path = tools_dir / f"{tool_name}.py"
                if temp_path.exists():
                    tool_path = temp_path
                    break

            if not tool_path:
                raise FileNotFoundError(f"No tool file found for: {tool_name}")

            logger.debug("tool_name=<%s> | reloading tool", tool_name)

            # Add tool directory to path temporarily
            tool_dir = str(tool_path.parent)
            sys.path.insert(0, tool_dir)
            try:
                # Load the module directly using spec
                spec = util.spec_from_file_location(tool_name, str(tool_path))
                if spec is None:
                    raise ImportError(f"Could not load spec for {tool_name}")

                module = util.module_from_spec(spec)
                sys.modules[tool_name] = module

                if spec.loader is None:
                    raise ImportError(f"Could not load {tool_name}")

                spec.loader.exec_module(module)

            finally:
                # Remove the temporary path
                sys.path.remove(tool_dir)

            # Look for function-based tools first
            try:
                function_tools = self._scan_module_for_tools(module)

                if function_tools:
                    for function_tool in function_tools:
                        # Register the function-based tool
                        self.register_tool(function_tool)

                        # Update tool configuration if available
                        if self.tool_config is not None:
                            self._update_tool_config(self.tool_config, {"spec": function_tool.tool_spec})

                    logger.debug("tool_name=<%s> | successfully reloaded function-based tool from module", tool_name)
                    return
            except ImportError:
                logger.debug("function tool loader not available | falling back to traditional tools")

            # Fall back to traditional module-level tools
            if not hasattr(module, "TOOL_SPEC"):
                raise ValueError(
                    f"Tool {tool_name} is missing TOOL_SPEC (neither at module level nor as a decorated function)"
                )

            expected_func_name = tool_name
            if not hasattr(module, expected_func_name):
                raise ValueError(f"Tool {tool_name} is missing {expected_func_name} function")

            tool_function = getattr(module, expected_func_name)
            if not callable(tool_function):
                raise ValueError(f"Tool {tool_name} function is not callable")

            # Validate tool spec
            self.validate_tool_spec(module.TOOL_SPEC)

            new_tool = PythonAgentTool(tool_name, module.TOOL_SPEC, tool_function)

            # Register the tool
            self.register_tool(new_tool)

            # Update tool configuration if available
            if self.tool_config is not None:
                self._update_tool_config(self.tool_config, {"spec": module.TOOL_SPEC})
            logger.debug("tool_name=<%s> | successfully reloaded tool", tool_name)

        except Exception:
            logger.exception("tool_name=<%s> | failed to reload tool", tool_name)
            raise</original>
<patched>    def reload_tool(self, tool_name: str) -> None:
        """Reload a specific tool module.

        Args:
            tool_name: Name of the tool to reload.

        Raises:
            FileNotFoundError: If the tool file cannot be found.
            ImportError: If there are issues importing the tool module.
            ValueError: If the tool specification is invalid or required components are missing.
            Exception: For other errors during tool reloading.
        """
        try:
            # Check for tool file
            logger.debug("tool_name=<%s> | searching directories for tool", tool_name)
            tools_dirs = self.get_tools_dirs()
            tool_path = None

            # Search for the tool file in all tool directories
            for tools_dir in tools_dirs:
                temp_path = tools_dir / f"{tool_name}.py"
                if temp_path.exists():
                    tool_path = temp_path
                    break

            if not tool_path:
                raise FileNotFoundError(f"No tool file found for: {tool_name}")

            logger.debug("tool_name=<%s> | reloading tool", tool_name)

            # Add tool directory to path temporarily
            tool_dir = str(tool_path.parent)
            sys.path.insert(0, tool_dir)
            try:
                # Load the module directly using spec
                spec = util.spec_from_file_location(tool_name, str(tool_path))
                if spec is None:
                    raise ImportError(f"Could not load spec for {tool_name}")

                module = util.module_from_spec(spec)
                sys.modules[tool_name] = module

                if spec.loader is None:
                    raise ImportError(f"Could not load {tool_name}")

                spec.loader.exec_module(module)

            finally:
                # Remove the temporary path
                sys.path.remove(tool_dir)

            # Look for function-based tools first
            try:
                function_tools = self._scan_module_for_tools(module)

                if function_tools:
                    for function_tool in function_tools:
                        # Atomically swap the function-based tool using register_tool (supports hot reload)
                        self.register_tool(function_tool)

                        # Update tool configuration if available
                        if self.tool_config is not None:
                            self._update_tool_config(self.tool_config, {"spec": function_tool.tool_spec})

                    logger.debug("tool_name=<%s> | successfully reloaded function-based tool from module", tool_name)
                    return
            except ImportError:
                logger.debug("function tool loader not available | falling back to traditional tools")

            # Fall back to traditional module-level tools
            if not hasattr(module, "TOOL_SPEC"):
                raise ValueError(
                    f"Tool {tool_name} is missing TOOL_SPEC (neither at module level nor as a decorated function)"
                )

            expected_func_name = tool_name
            if not hasattr(module, expected_func_name):
                raise ValueError(f"Tool {tool_name} is missing {expected_func_name} function")

            tool_function = getattr(module, expected_func_name)
            if not callable(tool_function):
                raise ValueError(f"Tool {tool_name} function is not callable")

            # Validate tool spec
            self.validate_tool_spec(module.TOOL_SPEC)

            new_tool = PythonAgentTool(tool_name, module.TOOL_SPEC, tool_function)

            # Atomically swap the traditional tool using register_tool (supports hot reload)
            self.register_tool(new_tool)

            # Update tool configuration if available
            if self.tool_config is not None:
                self._update_tool_config(self.tool_config, {"spec": module.TOOL_SPEC})
            logger.debug("tool_name=<%s> | successfully reloaded tool", tool_name)

        except Exception:
            logger.exception("tool_name=<%s> | failed to reload tool", tool_name)
            raise</patched>
```