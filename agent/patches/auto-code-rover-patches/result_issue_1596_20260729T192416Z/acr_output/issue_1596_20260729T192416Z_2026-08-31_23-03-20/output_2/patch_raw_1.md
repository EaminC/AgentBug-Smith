The main issue lies in the reasoning-acting loop exit condition inside the `_reply_impl` method (around line 753+). Currently, when a reasoning event yields a final `Msg` with no tool_use blocks, the loop exits immediately returning this message. This logic assumes the lack of tool_use means there must be visible text or user content, but the bug arises when the LLM returns a message containing only "thinking" blocks and no "text" or "tool_use" blocks. This leads to premature loop termination with an empty/thinking-only message.

The fix is to modify the exit condition to check if the final `Msg` contains any user-visible text blocks. Only if there is text content (not only thinking blocks) do we break the loop and return the message. Otherwise, we continue the loop to allow the model to produce a meaningful text or tool_use output.

We implement this by checking for `has_content_blocks("text")` on the final `Msg` before deciding to break from the loop on reasoning event `Msg`. If the final message contains no text blocks (only thinking blocks), continue the loop and do not break early.

We do this in the `_reply_impl` method inside the reasoning event processing section.

---

```
<file>src/agentscope/agent/_agent.py</file>
<original>
                        if isinstance(evt, Msg):
                            end_event = ReplyEndEvent(
                                session_id=self.state.session_id,
                                reply_id=self.state.reply_id,
                                finished_reason=ReplyEndReason.COMPLETED,
                            )
                            yield evt
                            return
</original>
<patched>
                        if isinstance(evt, Msg):
                            # Only exit if there is actual text content for the user
                            if evt.has_content_blocks("text"):
                                end_event = ReplyEndEvent(
                                    session_id=self.state.session_id,
                                    reply_id=self.state.reply_id,
                                    finished_reason=ReplyEndReason.COMPLETED,
                                )
                                yield evt
                                return
                            # else: only thinking blocks, continue the loop without breaking
</patched>
```