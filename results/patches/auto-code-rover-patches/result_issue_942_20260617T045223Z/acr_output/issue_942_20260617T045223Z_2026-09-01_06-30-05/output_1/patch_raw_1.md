```
<file>autogpt/agent/agent.py</file>
<original>
    def start_interaction_loop(self):
        ...
        thoughts = assistant_reply_json.get("thoughts", {})
        self_feedback_resp = self.get_self_feedback(
            thoughts, cfg.fast_llm_model
        )
        logger.typewriter_log(
            f"SELF FEEDBACK: {self_feedback_resp}",
        )
        ...
        result_tlength = count_string_tokens(
            str(command_result), cfg.fast_llm_model
        )
        memory_tlength = count_string_tokens(
            str(self.history.summary_message()), cfg.fast_llm_model
        )
        if result_tlength + memory_tlength + 600 > cfg.fast_token_limit:
            result = f"Failure: command {command_name} returned too much output. \
    ...
</original>
<patched>
    def start_interaction_loop(self):
        ...
        # Determine which model to use based on flags
        model_to_use = cfg.smart_llm_model  # Default to GPT-4
        if getattr(cfg, "gpt3only", False):
            model_to_use = cfg.fast_llm_model  # GPT-3.5 if gpt3only is set
        elif getattr(cfg, "gpt4only", False):
            model_to_use = cfg.smart_llm_model  # Explicit GPT-4

        thoughts = assistant_reply_json.get("thoughts", {})
        self_feedback_resp = self.get_self_feedback(
            thoughts, model_to_use
        )
        logger.typewriter_log(
            f"SELF FEEDBACK: {self_feedback_resp}",
        )
        ...
        result_tlength = count_string_tokens(
            str(command_result), model_to_use
        )
        memory_tlength = count_string_tokens(
            str(self.history.summary_message()), model_to_use
        )
        if result_tlength + memory_tlength + 600 > cfg.smart_token_limit if model_to_use == cfg.smart_llm_model else cfg.fast_token_limit:
            result = f"Failure: command {command_name} returned too much output. \
    ...
</patched>
```