The issue arises because the registration of the meta tool function `reset_equipped_tools` is enabled whenever `enable_meta_tool` is True or `plan_notebook` is provided. However, if `plan_notebook` is provided but `enable_meta_tool` is False, the plan tools are registered individually (not grouped under "plan_related"), so the earlier registration of `reset_equipped_tools` is ineffective.

Furthermore, when a user explicitly sets `enable_meta_tool` to False, but the system enables `reset_equipped_tools` anyway due to the presence of `plan_notebook`, the user should be notified, as it means the agent manages tools autonomously despite the user's intention.

**Proposed Fix:**
- Register `reset_equipped_tools` only if `enable_meta_tool` is True.
- When `plan_notebook` is set and `enable_meta_tool` is False, we do not register `reset_equipped_tools` because the meta tool is disabled and plan tools are always active individually.
- If the design requires that `reset_equipped_tools` be enabled when plan_notebook is set regardless of `enable_meta_tool`, we must notify the user accordingly so they're aware the meta tool functionality is effectively enabled.
- According to the issue description, we should at least inform the user if `reset_equipped_tools` is enabled due to plan_notebook even when `enable_meta_tool=False`.
- So the updated logic:
  - If `enable_meta_tool` is True, register `reset_equipped_tools` and setup "plan_related" tool group (if plan_notebook is present).
  - If `enable_meta_tool` is False but `plan_notebook` is provided, register `reset_equipped_tools` with a warning to inform the user the agent will manage tools autonomously.
  - Else, do not register `reset_equipped_tools`.

We will add an optional logging info or print statement to alert about the auto enablement.

**Implementation details:**
- Use the `logging` module to log a warning if the meta tool is effectively enabled due to plan_notebook despite `enable_meta_tool` being False.
- Adjust the conditions around `reset_equipped_tools` registration and tool group creation.
- Preserving existing behavior and safety.

---

# Patch

```
<file>src/agentscope/agent/_react_agent.py</file>
<original>        # -------------- Tool management --------------
        # If None, a default Toolkit will be created
        self.toolkit = toolkit or Toolkit()
        if self._agent_control:
            # Adding two tool functions into the toolkit to allow self-control
            self.toolkit.register_tool_function(
                long_term_memory.record_to_memory,
            )
            self.toolkit.register_tool_function(
                long_term_memory.retrieve_from_memory,
            )
        # Add a meta tool function to allow agent-controlled tool management
        if enable_meta_tool or plan_notebook:
            self.toolkit.register_tool_function(
                self.toolkit.reset_equipped_tools,
            )</original>
<patched>        import logging
        logger = logging.getLogger(__name__)

        # -------------- Tool management --------------
        # If None, a default Toolkit will be created
        self.toolkit = toolkit or Toolkit()
        if self._agent_control:
            # Adding two tool functions into the toolkit to allow self-control
            self.toolkit.register_tool_function(
                long_term_memory.record_to_memory,
            )
            self.toolkit.register_tool_function(
                long_term_memory.retrieve_from_memory,
            )
        # Add a meta tool function to allow agent-controlled tool management
        if enable_meta_tool:
            self.toolkit.register_tool_function(
                self.toolkit.reset_equipped_tools,
            )
        elif plan_notebook:
            # If meta tool is disabled but plan_notebook is provided, register reset_equipped_tools
            # to enable plans but inform user this overrides enable_meta_tool=False.
            self.toolkit.register_tool_function(
                self.toolkit.reset_equipped_tools,
            )
            logger.warning(
                "`reset_equipped_tools` has been enabled due to presence of plan_notebook, "
                "which means the agent will now manage tool groups autonomously, "
                "overriding enable_meta_tool=False."
            )
</patched>
```

```
<file>src/agentscope/agent/_react_agent.py</file>
<original>        # -------------- Plan management --------------
        # Equipped the plan-related tools provided by the plan notebook as
        # a tool group named "plan_related". So that the agent can activate
        # the plan tools by the meta tool function
        self.plan_notebook = None
        if plan_notebook:
            self.plan_notebook = plan_notebook
            # When enable_meta_tool is True, plan tools are in plan_related
            # group and active by agent.
            # Otherwise, plan tools in bassic group and always active.
            if enable_meta_tool:
                self.toolkit.create_tool_group(
                    "plan_related",
                    description=self.plan_notebook.description,
                )
                for tool in plan_notebook.list_tools():
                    self.toolkit.register_tool_function(
                        tool,
                        group_name="plan_related",
                    )
            else:
                for tool in plan_notebook.list_tools():
                    self.toolkit.register_tool_function(
                        tool,
                    )</original>
<patched>        # -------------- Plan management --------------
        # Equipped the plan-related tools provided by the plan notebook as
        # a tool group named "plan_related". So that the agent can activate
        # the plan tools by the meta tool function
        self.plan_notebook = None
        if plan_notebook:
            self.plan_notebook = plan_notebook
            # When enable_meta_tool is True, plan tools are in plan_related
            # group and active by agent.
            # Otherwise, plan tools in bassic group and always active.
            if enable_meta_tool:
                self.toolkit.create_tool_group(
                    "plan_related",
                    description=self.plan_notebook.description,
                )
                for tool in plan_notebook.list_tools():
                    self.toolkit.register_tool_function(
                        tool,
                        group_name="plan_related",
                    )
            else:
                # Plan tools always active individually when meta tool is disabled
                for tool in plan_notebook.list_tools():
                    self.toolkit.register_tool_function(
                        tool,
                    )</patched>
```

---

This patch addresses the logical conflict by:
- Registering `reset_equipped_tools` only once with a clear indication when it's enabled due to plan_notebook overriding `enable_meta_tool`.
- Keeping the plan tool registration consistent with `enable_meta_tool` for grouping.
- Adding a warning message to inform users about the implicit override for clarity.