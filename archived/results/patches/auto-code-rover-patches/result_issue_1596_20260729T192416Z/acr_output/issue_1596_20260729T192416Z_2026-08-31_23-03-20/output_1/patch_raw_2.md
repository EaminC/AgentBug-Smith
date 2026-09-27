```
<file>src/agentscope/agent/_agent.py</file>
<original>                                    elif not msg_reasoning.has_content_blocks("tool_use"):
                                        # Exit the loop when no structured output is required (or
                                        # already satisfied) and only text response is generated
                                        msg_reasoning.metadata = structured_output
                                        reply_msg = msg_reasoning
                                        break
</original>
<patched>                                    elif not msg_reasoning.has_content_blocks("tool_use"):
                                        # Only exit if there's actual text content for the user
                                        if msg_reasoning.has_content_blocks("text"):
                                            msg_reasoning.metadata = structured_output
                                            reply_msg = msg_reasoning
                                            break
                                        # else: only thinking blocks present, continue the loop
</patched>
```
Reasoning:

The problem occurs because the main agent loop exits whenever there is no "tool_use" block in the response regardless of whether there is meaningful text. When only "thinking" blocks are present (no tool_use and no text), the current exit condition treats it as done, causing the loop to break prematurely and return an empty or non-informative response.

To fix this, the loop exit condition should be altered to verify that the response message actually contains user-visible "text" content when no "tool_use" blocks exist. If the response contains only "thinking" blocks and no "text", the loop should continue to allow further iterations until meaningful output appears. This sequentially allows models with thinking capabilities to produce intermediate "thinking" blocks without finalizing the response early.

This patch small and surgical preserves original behavior when valid text or tool_use is present but avoids breaking the loop prematurely when only thinking blocks are output.