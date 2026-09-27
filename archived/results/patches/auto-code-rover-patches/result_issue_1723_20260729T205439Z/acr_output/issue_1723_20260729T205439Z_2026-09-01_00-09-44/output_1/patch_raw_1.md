```
<file>src/agentscope/agent/_agent.py</file>
<original>    async def compress_context(
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
        cfg: ContextConfig = context_config or self.context_config

        # Count the current tokens
        kwargs = await self._prepare_model_input()
        estimated_tokens = await self.model.count_tokens(**kwargs)

        # Skip if no compression is needed
        threshold = cfg.trigger_ratio * self.model.context_size
        if estimated_tokens < threshold:
            return

        logger.info(
            "[AGENT %s]: Current token count %d exceeds the threshold %d, "
            "activating compression.",
            self.name,
            int(estimated_tokens),
            int(threshold),
        )

        if len(self.state.context) == 0:
            # The system prompt and the summary (if exists) exceeds the
            # threshold, which cannot be compressed, raise the error to the
            # developer!
            suffix = ""
            if self.state.summary:
                suffix = "and the compression summary "
            raise RuntimeError(
                f"The system prompt {suffix}exceed(s) the compression "
                f"threshold ({threshold} tokens), cannot be compressed.",
            )

        # Split the context into the ones to be compressed, and the others to
        # be reserved
        tools = kwargs.get("tools", [])
        (
            msgs_to_compress,
            msgs_to_reserve,
        ) = await self._split_context_for_compression(
            cfg.reserve_ratio * self.model.context_size,
            tools,
        )

        if len(msgs_to_compress) == 0:
            # The reserve ratio is too large so that although it exceeds the
            # trigger threshold, the context to be compressed is empty
            # Fallback by lowering the reserve ratio to compress more context.
            logger.warning(
                "The reserve ratio %.2f is too large to compress any context."
                "Lower the reserve ratio to 0 as a fallback.",
                cfg.reserve_ratio,
            )
            (
                msgs_to_compress,
                msgs_to_reserve,
            ) = await self._split_context_for_compression(
                0 * self.model.context_size,
                tools,
            )

            # The msgs to be compressed cannot be empty here, unless the
            # system prompt and summary (if any) already exceed the context
            # length, which we have handled before.

        # Prepare the messages to compress
        msgs_system = [
            SystemMsg(
                name="system",
                content=await self._get_system_prompt(),
            ),
        ]
        if self.state.summary:
            msgs_system.append(UserMsg("user", self.state.summary))

        messages = (
            msgs_system
            + msgs_to_compress
            + [
                UserMsg(name="user", content=cfg.compression_prompt),
            ]
        )

        # The compression prompt may exceed the context length, here we mark
        # the overflow by a bool flag
        compression_tool_schema = [
            {
                "type": "function",
                "function": {
                    "name": "generate_structured_output",
                    "description": "Call this function to generate "
                    "structured output required by "
                    "the user.",
                    "parameters": cfg.summary_schema,
                },
            },
        ]
        context_overflow = False
        estimated_compression_tokens = await self.model.count_tokens(
            messages,
            compression_tool_schema,
        )
        if estimated_compression_tokens > self.model.context_size:
            logger.warning(
                "The current context length exceeds the model's context "
                "length (%d tokens), the compression maybe failed due to "
                "insufficient reserved context for compression.",
                self.model.context_size,
            )
            context_overflow = True

        # Compress the messages
        try:
            res = await self.model.generate_structured_output(
                messages=messages,
                structured_model=cfg.summary_schema,
            )

        except Exception as e:
            if context_overflow:
                logger.warning(
                    "Failed to compress context, which may be caused by "
                    "insufficient reserved context for compression. "
                    "Trying to compress by removing the oldest context.",
                )
                for i in range(1, len(msgs_to_compress) + 1):
                    messages = (
                        msgs_system
                        + msgs_to_compress[i:]
                        + [
                            UserMsg(
                                name="user",
                                content=cfg.compression_prompt,
                            ),
                        ]
                    )
                    estimated_compression_tokens = (
                        await self.model.count_tokens(
                            messages,
                            compression_tool_schema,
                        )
                    )
                    # Considering trigger_ratio <= 0.9, at least reserve 10%
                    # tokens for compression response
                    if (
                        estimated_compression_tokens
                        < self.model.context_size * cfg.trigger_ratio
                    ):
                        break

                res = await self.model.generate_structured_output(
                    messages=messages,
                    structured_model=cfg.summary_schema,
                )

            else:
                raise e from None

        # Update the summary
        self.state.summary = cfg.summary_template.format(**res.content)

        if self.offloader:
            path = await self.offloader.offload_context(
                self.state.session_id,
                msgs=msgs_to_compress,
            )

            self.state.summary += (
                f"\n<system-reminder>The compressed context is offloaded to "
                f"'{path}', you can refer to it when needed.</system-reminder>"
            )

        # Update the context
        self.state.context = msgs_to_reserve

        logger.info(
            "[AGENT %s]: The context compression finished.",
            self.name,
        )
</original>
<patched>    async def compress_context(
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
        cfg: ContextConfig = context_config or self.context_config

        # Count the current tokens
        kwargs = await self._prepare_model_input()
        estimated_tokens = await self.model.count_tokens(**kwargs)

        # Skip if no compression is needed
        threshold = cfg.trigger_ratio * self.model.context_size
        if estimated_tokens < threshold:
            return

        logger.info(
            "[AGENT %s]: Current token count %d exceeds the threshold %d, "
            "activating compression.",
            self.name,
            int(estimated_tokens),
            int(threshold),
        )

        if len(self.state.context) == 0:
            # The system prompt and the summary (if exists) exceeds the
            # threshold, which cannot be compressed, raise the error to the
            # developer!
            suffix = ""
            if self.state.summary:
                suffix = "and the compression summary "
            raise RuntimeError(
                f"The system prompt {suffix}exceed(s) the compression "
                f"threshold ({threshold} tokens), cannot be compressed.",
            )

        # Split the context into the ones to be compressed, and the others to
        # be reserved
        tools = kwargs.get("tools", [])
        (
            msgs_to_compress,
            msgs_to_reserve,
        ) = await self._split_context_for_compression(
            cfg.reserve_ratio * self.model.context_size,
            tools,
        )

        if len(msgs_to_compress) == 0:
            # The reserve ratio is too large so that although it exceeds the
            # trigger threshold, the context to be compressed is empty
            # Fallback by lowering the reserve ratio to compress more context.
            logger.warning(
                "The reserve ratio %.2f is too large to compress any context."
                "Lower the reserve ratio to 0 as a fallback.",
                cfg.reserve_ratio,
            )
            (
                msgs_to_compress,
                msgs_to_reserve,
            ) = await self._split_context_for_compression(
                0 * self.model.context_size,
                tools,
            )

            # The msgs to be compressed cannot be empty here, unless the
            # system prompt and summary (if any) already exceed the context
            # length, which we have handled before.

        # Identify and clear cache for evicted Read tool call blocks
        from src.agentscope.message._block import ToolCallBlock
        for msg in msgs_to_compress:
            # Only handle tool call blocks
            if isinstance(msg, ToolCallBlock):
                if msg.name == "read":
                    # Clear cached read file content related to this tool call block
                    # The cache is stored in agent state under read_file_cache
                    # Remove entries whose file_path matches the input specified in tool call
                    # The input is a JSON string; parse it to get the file_path
                    import json
                    try:
                        input_data = json.loads(msg.input)
                    except Exception:
                        input_data = {}
                    file_path = input_data.get("file_path")
                    if file_path:
                        # Remove cached entries for this file_path in agent state
                        self.state.read_file_cache = [
                            entry for entry in self.state.read_file_cache if entry.file_path != file_path
                        ]

        # Prepare the messages to compress
        msgs_system = [
            SystemMsg(
                name="system",
                content=await self._get_system_prompt(),
            ),
        ]
        if self.state.summary:
            msgs_system.append(UserMsg("user", self.state.summary))

        messages = (
            msgs_system
            + msgs_to_compress
            + [
                UserMsg(name="user", content=cfg.compression_prompt),
            ]
        )

        # The compression prompt may exceed the context length, here we mark
        # the overflow by a bool flag
        compression_tool_schema = [
            {
                "type": "function",
                "function": {
                    "name": "generate_structured_output",
                    "description": "Call this function to generate "
                    "structured output required by "
                    "the user.",
                    "parameters": cfg.summary_schema,
                },
            },
        ]
        context_overflow = False
        estimated_compression_tokens = await self.model.count_tokens(
            messages,
            compression_tool_schema,
        )
        if estimated_compression_tokens > self.model.context_size:
            logger.warning(
                "The current context length exceeds the model's context "
                "length (%d tokens), the compression maybe failed due to "
                "insufficient reserved context for compression.",
                self.model.context_size,
            )
            context_overflow = True

        # Compress the messages
        try:
            res = await self.model.generate_structured_output(
                messages=messages,
                structured_model=cfg.summary_schema,
            )

        except Exception as e:
            if context_overflow:
                logger.warning(
                    "Failed to compress context, which may be caused by "
                    "insufficient reserved context for compression. "
                    "Trying to compress by removing the oldest context.",
                )
                for i in range(1, len(msgs_to_compress) + 1):
                    messages = (
                        msgs_system
                        + msgs_to_compress[i:]
                        + [
                            UserMsg(
                                name="user",
                                content=cfg.compression_prompt,
                            ),
                        ]
                    )
                    estimated_compression_tokens = (
                        await self.model.count_tokens(
                            messages,
                            compression_tool_schema,
                        )
                    )
                    # Considering trigger_ratio <= 0.9, at least reserve 10%
                    # tokens for compression response
                    if (
                        estimated_compression_tokens
                        < self.model.context_size * cfg.trigger_ratio
                    ):
                        break

                res = await self.model.generate_structured_output(
                    messages=messages,
                    structured_model=cfg.summary_schema,
                )

            else:
                raise e from None

        # Update the summary
        self.state.summary = cfg.summary_template.format(**res.content)

        if self.offloader:
            path = await self.offloader.offload_context(
                self.state.session_id,
                msgs=msgs_to_compress,
            )

            self.state.summary += (
                f"\n<system-reminder>The compressed context is offloaded to "
                f"'{path}', you can refer to it when needed.</system-reminder>"
            )

        # Update the context
        self.state.context = msgs_to_reserve

        logger.info(
            "[AGENT %s]: The context compression finished.",
            self.name,
        )
</patched>
```