```
<file>src/agentscope/agent/_agent.py</file>
<original>
    async def compress_context(
        self,
        context_config: ContextConfig | None = None,
    ) -> None:
        """Compress the agent's context if the token count exceeds the
        threshold.

        Args:
            context_config (`ContextConfig | None`, optional):
                If provided, compress the context with the given context
                config. Otherwise, use the default context config in the
                agent.
        """
        if not self._compress_context_middlewares:
            await self._compress_context_impl(context_config=context_config)
        else:

            async def execute_chain(
                index: int = 0,
                context_config: ContextConfig | None = context_config,
            ) -> None:
                """Execute the compress_context middleware chain."""
                if index >= len(self._compress_context_middlewares):
                    await self._compress_context_impl(
                        context_config=context_config,
                    )
                else:
                    mw = self._compress_context_middlewares[index]
                    input_kwargs = {"context_config": context_config}

                    async def next_handler(**kwargs: Any) -> None:
                        await execute_chain(index + 1, **kwargs)

                    await mw.on_compress_context(
                        agent=self,
                        input_kwargs=input_kwargs,
                        next_handler=next_handler,
                    )

            await execute_chain()
</original>
<patched>
    async def compress_context(
        self,
        context_config: ContextConfig | None = None,
        instructions: HintBlock | None = None,
    ) -> None:
        """Compress the agent's context if the token count exceeds the
        threshold.

        Args:
            context_config (`ContextConfig | None`, optional):
                If provided, compress the context with the given context
                config. Otherwise, use the default context config in the
                agent.
            instructions (`HintBlock | None`, optional):
                User-defined hints or instructions to guide the context compression.
        """
        if not self._compress_context_middlewares:
            await self._compress_context_impl(
                context_config=context_config,
                instructions=instructions,
            )
        else:

            async def execute_chain(
                index: int = 0,
                context_config: ContextConfig | None = context_config,
                instructions: HintBlock | None = instructions,
            ) -> None:
                """Execute the compress_context middleware chain."""
                if index >= len(self._compress_context_middlewares):
                    await self._compress_context_impl(
                        context_config=context_config,
                        instructions=instructions,
                    )
                else:
                    mw = self._compress_context_middlewares[index]
                    input_kwargs = {"context_config": context_config, "instructions": instructions}

                    async def next_handler(**kwargs: Any) -> None:
                        await execute_chain(index + 1, **kwargs)

                    await mw.on_compress_context(
                        agent=self,
                        input_kwargs=input_kwargs,
                        next_handler=next_handler,
                    )

            await execute_chain()
</patched>
```

```
<file>src/agentscope/agent/_agent.py</file>
<original>
    async def _compress_context_impl(
        self,
        context_config: ContextConfig | None = None,
    ) -> None:
        ...
</original>
<patched>
    async def _compress_context_impl(
        self,
        context_config: ContextConfig | None = None,
        instructions: HintBlock | None = None,
    ) -> None:
        ...
</patched>
```

Explanation:

The main method `compress_context` is extended with an optional `instructions` parameter of type `HintBlock` that can take user-defined hints to guide context compression. This parameter is added to the method signature, the middleware chain invocation, and passed down to the internal implementation `_compress_context_impl`.

Similarly, the internal compression method `_compress_context_impl` is updated to accept this new argument. The actual handling logic of the `instructions` parameter should be added within `_compress_context_impl`, but this patch scopes only to signature update and parameter propagation as the internals aren't visible here.

Middleware invocations also receive the `instructions` argument via `input_kwargs` to allow any middleware to access and use the user-defined compression hints.

This approach preserves existing functionality by making the `instructions` argument optional and only augmenting the compression flow with additional guidance.