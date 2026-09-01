```
<file>src/agentscope/tool/_builtin/_backend.py</file>
<original>    async def exec_shell(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        """Run a program via ``asyncio.create_subprocess_exec``.
        
        The program is spawned directly from *command* without an
        intervening shell, so no argument quoting is required and the
        same code path works on POSIX and Windows.
        
        Args:
            command (`list[str]`):
                Executable path/name followed by its arguments.
            cwd (`str | None`, optional):
                Working directory for the subprocess. When ``None`` the
                current process working directory is used.
            timeout (`float | None`, optional):
                Maximum number of seconds to wait before the process is
                killed and an ``exit_code`` of ``-1`` is returned.
        
        Returns:
            `ExecResult`:
                The captured exit code, stdout, and stderr. If the
                executable cannot be found or spawned, ``exit_code`` is
                ``127`` (matching a shell's "command not found"), with
                the OS error message on stderr.
        """
        kwargs = _subprocess_creation_kwargs()
        if cwd is not None:
            kwargs["cwd"] = cwd
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs,
</original>
<patched>    async def exec_shell(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        """Run a program via ``asyncio.create_subprocess_exec``.
        
        The program is spawned directly from *command* without an
        intervening shell, so no argument quoting is required and the
        same code path works on POSIX and Windows.
        
        For Windows, if the command is intended to be a PowerShell script or
        command, it will execute using PowerShell executable.
        
        Args:
            command (`list[str]`):
                Executable path/name followed by its arguments.
            cwd (`str | None`, optional):
                Working directory for the subprocess. When ``None`` the
                current process working directory is used.
            timeout (`float | None`, optional):
                Maximum number of seconds to wait before the process is
                killed and an ``exit_code`` of ``-1`` is returned.
        
        Returns:
            `ExecResult`:
                The captured exit code, stdout, and stderr. If the
                executable cannot be found or spawned, ``exit_code`` is
                ``127`` (matching a shell's "command not found"), with
                the OS error message on stderr.
        """
        import sys

        # Detect if we are running on Windows and use PowerShell accordingly
        if sys.platform.startswith("win") and command:
            # Check if command is a PowerShell tool invocation (heuristic):
            # For safety, you might want to define a convention or a wrapper
            # but here we assume that if the executable is 'powershell' or desired,
            # or we want to run all via powershell, or alternatively if first command is not exe.
            # For simplicity, if the first command is 'pwsh' or 'powershell' or endswith .ps1
            # Usually the Bash tool runs with "bash" which we do not invoke here directly.
            # Instead, if command is not a direct executable but a script to run, wrap it.

            ps_commands = {"powershell", "pwsh"}
            first_cmd = command[0].lower()
            if (
                first_cmd in ps_commands
                or first_cmd.endswith(".ps1")
                or "powershell" in first_cmd
            ):
                # For direct PowerShell commands, run as is without wrapping
                pass
            else:
                # Wrap arbitrary command list to a PowerShell command invocation
                # Join arguments carefully to a PowerShell command string
                import shlex

                ps_command_str = " ".join(shlex.quote(arg) for arg in command)
                command = [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    ps_command_str,
                ]

        kwargs = _subprocess_creation_kwargs()
        if cwd is not None:
            kwargs["cwd"] = cwd
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs,
</patched>
```

```
<file>src/agentscope/tool/_builtin/_bash.py</file>
<original>
25 class Bash(ToolBase):
26     """The bash tool."""
27 
28     name: str = "Bash"
</original>
<patched>
25 class Bash(ToolBase):
26     """The bash tool."""
27 
28     name: str = "Bash"
29 
30 
31 class PowerShell(ToolBase):
32     """The PowerShell tool for Windows."""
33 
34     name: str = "PowerShell"
35 
36     async def run(self, command: str) -> str:
37         """Run the specified PowerShell command asynchronously."""
38         import asyncio
39         from src.agentscope.tool._builtin._backend import LocalBackend
40 
41         backend = LocalBackend()
42         exec_result = await backend.exec_shell(
43             ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
44         )
45         if exec_result.exit_code != 0:
46             raise RuntimeError(
47                 f"PowerShell command failed: {exec_result.stderr.decode()}"
48             )
49         return exec_result.stdout.decode()
</patched>
```

```
<file>src/agentscope/tool/_toolkit.py</file>
<original>
128             ToolGroup(
129                 name="basic",
130                 tools=tools or [],
131                 skills_or_loaders=skills_or_loaders or [],
132                 mcps=mcps or [],
133             ),
134         ] + (tool_groups or [])
</original>
<patched>
128             ToolGroup(
129                 name="basic",
130                 tools=tools or [],
131                 skills_or_loaders=skills_or_loaders or [],
132                 mcps=mcps or [],
133             ),
134         ] + (tool_groups or [])

    import sys
    from ._builtin._bash import Bash
    try:
        from ._builtin._powershell import PowerShell  # Assuming PowerShell tool moved here if separated
    except ImportError:
        # No PowerShell tool found; fallback if needed
        PowerShell = None

    # On Windows, if no tools are provided, default to PowerShell tool,
    # else if on other OS, default to Bash if no tools provided.
    if tools is None or len(tools) == 0:
        if sys.platform.startswith("win"):
            tools = [PowerShell()] if PowerShell is not None else []
        else:
            tools = [Bash()]

    # Replace tools for "basic" group accordingly
    self.tool_groups[0].tools = tools
</patched>
```