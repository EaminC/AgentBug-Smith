```
<file>autogpt/agent/agent.py</file>
<original>
    def start_interaction_loop(self) -> None:
        ...
        thoughts = assistant_reply_json.get("thoughts", {})
        self_feedback_resp = self.get_self_feedback(
            thoughts, cfg.fast_llm_model
        )
        logger.typewriter_log(
            f"SELF FEEDBACK: {self_feedback_resp}",
</original>
<patched>
    def start_interaction_loop(self) -> None:
        ...
        # Determine correct model to use according to configuration flags
        model_to_use = cfg.smart_llm_model  # Default GPT-4
        if getattr(cfg, "gpt3only", False):
            model_to_use = cfg.fast_llm_model  # Force GPT-3.5 if flag set
        elif getattr(cfg, "gpt4only", False):
            model_to_use = cfg.smart_llm_model  # Force GPT-4 if flag set (redundant but explicit)

        thoughts = assistant_reply_json.get("thoughts", {})
        self_feedback_resp = self.get_self_feedback(
            thoughts, model_to_use
        )
        logger.typewriter_log(
            f"SELF FEEDBACK: {self_feedback_resp}",
</patched>
```

```
<file>autogpt/agent/agent.py</file>
<original>
    def start_interaction_loop(self) -> None:
        ...
        result_tlength = count_string_tokens(
            str(command_result), cfg.fast_llm_model
        )
        memory_tlength = count_string_tokens(
            str(self.history.summary_message()), cfg.fast_llm_model
        )
        if result_tlength + memory_tlength + 600 > cfg.fast_token_limit:
            result = f"Failure: command {command_name} returned too much output. \

</original>
<patched>
    def start_interaction_loop(self) -> None:
        ...
        # Use the same model_to_use for token counting for consistency
        model_to_use = cfg.smart_llm_model  # Default GPT-4
        if getattr(cfg, "gpt3only", False):
            model_to_use = cfg.fast_llm_model

        result_tlength = count_string_tokens(
            str(command_result), model_to_use
        )
        memory_tlength = count_string_tokens(
            str(self.history.summary_message()), model_to_use
        )
        token_limit = cfg.smart_token_limit if model_to_use == cfg.smart_llm_model else cfg.fast_token_limit
        if result_tlength + memory_tlength + 600 > token_limit:
            result = f"Failure: command {command_name} returned too much output. \

</patched>
```