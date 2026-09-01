```
<file>src/strands/agent/agent.py</file>
<original>
656         finally:
657             self.conversation_manager.apply_management(self)
658             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
</original>
<patched>
656         finally:
657             # Allow conversation management to be applied before and also during AfterInvocationEvent hooks
658             # to reduce messages during the loop execution dynamically.
659             # Call apply_management before hooks as original.
660             self.conversation_manager.apply_management(self)
661             # Provide a synchronous apply_management call hook before invoking callbacks asynchronously,
662             # so users can perform message pruning inside AfterInvocationEvent callbacks effectively.
663             result = AfterInvocationEvent(agent=self, result=agent_result)
664             await self.hooks.invoke_callbacks_async(result)
665             # Apply management again after callbacks to apply any changes done in hooks
666             self.conversation_manager.apply_management(self)
</patched>
```

Reasoning:

The original code calls conversation_manager.apply_management once before the AfterInvocationEvent hooks are invoked asynchronously. The user reported that calling apply_management inside AfterInvocationEvent hook callbacks does not work effectively because messages are already managed before the hook calls, so dynamic mid-loop management is not achieved.

The patch adds a second call to conversation_manager.apply_management immediately after the asynchronous AfterInvocationEvent callbacks finish, so if any hook callback calls or triggers message changes that require conversation management, they will be applied promptly. This ensures dynamic management during loop execution.

This approach preserves existing behavior (management before hooks) and extends it so that calling apply_management within AfterInvocationEvent hooks or changes triggered by them will effectively reduce the message list dynamically, addressing the bug without breaking existing logic.