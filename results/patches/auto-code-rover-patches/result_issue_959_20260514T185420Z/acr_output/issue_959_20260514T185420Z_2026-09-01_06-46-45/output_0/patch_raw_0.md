Reasoning:
The issue states that the `reset_equipped_tools` method activates specified tool groups but does not deactivate the previously active tool groups that are not included in the current activation list. This can result in lingering active groups when `reset_equipped_tools` is called multiple times. Since the method is intended to "reset" the tool groups, it should deactivate all tool groups first (except the 'basic' group which should always remain active), and then activate the requested groups. 

The current implementation of `update_tool_groups` simply sets active status for given groups but doesn't handle deactivating groups not in the list. 

Thus, the fix is to modify `reset_equipped_tools` method to:
- Deactivate all groups except 'basic'
- Activate only the requested groups

This ensures a full reset of active tool groups according to provided boolean flags.

No changes are needed to `update_tool_groups` other than its current behavior; `reset_equipped_tools` can handle deactivation explicitly.

---

Patch:

```
<file>src/agentscope/tool/_toolkit.py</file>
<original>    def reset_equipped_tools(self, **kwargs: Any) -> ToolResponse:
        """Choose appropriate tools to equip yourself with, so that you can
        finish your task. Each argument in this function represents a group
        of related tools, and the value indicates whether to activate the
        group or not. Besides, the tool response of this function will
        contain the precaution notes for using them, which you
        **MUST pay attention to and follow**. You can also reuse this function
        to check the notes of the tool groups.

        Note this function will `reset` the tools, so that the original tools
        will be removed first.
        """

        to_activate = []
        for key, value in kwargs.items():
            if not isinstance(value, bool):
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Invalid arguments: the argument {key} "
                            f"should be a bool value, but got {type(value)}.",
                        ),
                    ],
                )

            if value:
                to_activate.append(key)

        self.update_tool_groups(to_activate, active=True)

        notes = self.get_activated_notes()

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Active tool groups successfully: {to_activate}. "
                    "You MUST follow these notes to use the tools:\n"
                    f"<notes>{notes}</notes>",
                ),
            ],
        )
</original>
<patched>    def reset_equipped_tools(self, **kwargs: Any) -> ToolResponse:
        """Choose appropriate tools to equip yourself with, so that you can
        finish your task. Each argument in this function represents a group
        of related tools, and the value indicates whether to activate the
        group or not. Besides, the tool response of this function will
        contain the precaution notes for using them, which you
        **MUST pay attention to and follow**. You can also reuse this function
        to check the notes of the tool groups.

        Note this function will `reset` the tools, so that the original tools
        will be removed first.
        """

        to_activate = []
        for key, value in kwargs.items():
            if not isinstance(value, bool):
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Invalid arguments: the argument {key} "
                            f"should be a bool value, but got {type(value)}.",
                        ),
                    ],
                )

            if value:
                to_activate.append(key)

        # Deactivate all groups except 'basic'
        for group_name, group in self.groups.items():
            if group_name != "basic":
                group.active = False

        # Activate specified groups
        self.update_tool_groups(to_activate, active=True)

        notes = self.get_activated_notes()

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Active tool groups successfully: {to_activate}. "
                    "You MUST follow these notes to use the tools:\n"
                    f"<notes>{notes}</notes>",
                ),
            ],
        )
</patched>
```