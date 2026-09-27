Reasoning:

To add support for setting a current working directory (cwd) in the Bash tool, two primary updates are needed:

1. Modify the `Bash` class constructor (`__init__`) to accept an optional `cwd` parameter and store it as an instance attribute.
2. Update the asynchronous `__call__` method where the subprocess is created to pass the `cwd` argument (if set) to the `asyncio.create_subprocess_shell` call. This enables commands to be executed in the specified working directory.

This approach preserves existing behavior when cwd is not provided and seamlessly adds support for specifying it.

---

Patch:

```
<file>src/agentscope/tool/_builtin/_bash.py</file>
<original>    def __init__(  # pylint: disable=dangerous-default-value
        self,
        dangerous_files: list[str] = DEFAULT_DANGEROUS_FILES,
        dangerous_directories: list[str] = DEFAULT_DANGEROUS_DIRECTORIES,
    ) -> None:
        """Initialize the bash tool.

        Args:
            dangerous_files (`list[str]`, optional):
                Sensitive files that require explicit user confirmation,
                even in BYPASS mode. Matched by basename
                (case-insensitive). Defaults to `DEFAULT_DANGEROUS_FILES`.
                Pass a custom list to fully replace the defaults, or `[]`
                to disable the filename check.
            dangerous_directories (`list[str]`, optional):
                Sensitive directories that require explicit user
                confirmation. Matched when any path segment equals an
                entry (case-insensitive). Defaults to
                `DEFAULT_DANGEROUS_DIRECTORIES`. Pass a custom list to
                fully replace the defaults, or `[]` to disable the
                directory check.
        """

        self._bash_parser = BashCommandParser()

        self.dangerous_files = list(dangerous_files)
        self.dangerous_directories = list(dangerous_directories)
</original>
<patched>    def __init__(  # pylint: disable=dangerous-default-value
        self,
        dangerous_files: list[str] = DEFAULT_DANGEROUS_FILES,
        dangerous_directories: list[str] = DEFAULT_DANGEROUS_DIRECTORIES,
        cwd: str | None = None,
    ) -> None:
        """Initialize the bash tool.

        Args:
            dangerous_files (`list[str]`, optional):
                Sensitive files that require explicit user confirmation,
                even in BYPASS mode. Matched by basename
                (case-insensitive). Defaults to `DEFAULT_DANGEROUS_FILES`.
                Pass a custom list to fully replace the defaults, or `[]`
                to disable the filename check.
            dangerous_directories (`list[str]`, optional):
                Sensitive directories that require explicit user
                confirmation. Matched when any path segment equals an
                entry (case-insensitive). Defaults to
                `DEFAULT_DANGEROUS_DIRECTORIES`. Pass a custom list to
                fully replace the defaults, or `[]` to disable the
                directory check.
            cwd (`str`, optional):
                The current working directory for executing bash commands.
        """

        self._bash_parser = BashCommandParser()

        self.dangerous_files = list(dangerous_files)
        self.dangerous_directories = list(dangerous_directories)
        self.cwd = cwd
</patched>
```

```
<file>src/agentscope/tool/_builtin/_bash.py</file>
<original>        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **_subprocess_creation_kwargs(),
            )
</original>
<patched>        try:
            # Create subprocess
            creation_kwargs = _subprocess_creation_kwargs()
            if self.cwd is not None:
                creation_kwargs["cwd"] = self.cwd

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **creation_kwargs,
            )
</patched>
```