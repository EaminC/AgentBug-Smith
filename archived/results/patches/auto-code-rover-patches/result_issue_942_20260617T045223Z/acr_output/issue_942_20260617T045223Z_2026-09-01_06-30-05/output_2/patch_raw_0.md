```
<file>autogpt/llm/api_manager.py</file>
<original>
    def create_chat_completion(
        self,
        messages: list[MessageDict],
        model: str | None = None,
        temperature: float = None,
        max_tokens: int | None = None,
        deployment_id=None,
    ) -> str:
        """
        Create a chat completion and update the cost.
        Args:
        messages (list): The list of messages to send to the API.
        model (str): The model to use for the API call.
        temperature (float): The temperature to use for the API call.
        max_tokens (int): The maximum number of tokens for the API call.
        Returns:
        str: The AI's response.
        """
        cfg = Config()
        if temperature is None:
            temperature = cfg.temperature
        if deployment_id is not None:
            response = openai.ChatCompletion.create(
                deployment_id=deployment_id,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=cfg.openai_api_key,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=cfg.openai_api_key,
            )
        if not hasattr(response, "error"):
            logger.debug(f"Response: {response}")
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            self.update_cost(prompt_tokens, completion_tokens, model)
        return response
</original>
<patched>
    def create_chat_completion(
        self,
        messages: list[MessageDict],
        model: str | None = None,
        temperature: float = None,
        max_tokens: int | None = None,
        deployment_id=None,
    ) -> str:
        """
        Create a chat completion and update the cost.
        Args:
        messages (list): The list of messages to send to the API.
        model (str): The model to use for the API call.
        temperature (float): The temperature to use for the API call.
        max_tokens (int): The maximum number of tokens for the API call.
        Returns:
        str: The AI's response.
        """
        cfg = Config()

        # If no model explicitly provided, select preferred default model
        if model is None:
            # Default to smart_llm_model (GPT-4) when no flags force otherwise
            model = cfg.smart_llm_model

        if temperature is None:
            temperature = cfg.temperature
        if deployment_id is not None:
            response = openai.ChatCompletion.create(
                deployment_id=deployment_id,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=cfg.openai_api_key,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=cfg.openai_api_key,
            )
        if not hasattr(response, "error"):
            logger.debug(f"Response: {response}")
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            self.update_cost(prompt_tokens, completion_tokens, model)
        return response
</patched>
```

```
<file>autogpt/agent/agent.py</file>
<original>
    def get_self_feedback(self, thoughts: dict, llm_model: str) -> str:
        """Generates a feedback response based on the provided thoughts dictionary.
        This method takes in a dictionary of thoughts containing keys such as 'reasoning',
        'plan', 'thoughts', and 'criticism'. It combines these elements into a single
        feedback message and uses the create_chat_completion() function to generate a
        response based on the input message.
        Args:
            thoughts (dict): A dictionary containing thought elements like reasoning,
            plan, thoughts, and criticism.
        Returns:
            str: A feedback response generated using the provided thoughts dictionary.
        """
        ai_role = self.config.ai_role

        feedback_prompt = f"Below is a message from me, an AI Agent, assuming the role of {ai_role}. whilst keeping knowledge of my slight limitations as an AI Agent Please evaluate my thought process, reasoning, and plan, and provide a concise paragraph outlining potential improvements. Consider adding or removing ideas that do not align with my role and explaining why, prioritizing thoughts based on their significance, or simply refining my overall thought process."
        reasoning = thoughts.get("reasoning", "")
        plan = thoughts.get("plan", "")
        thought = thoughts.get("thoughts", "")
        feedback_thoughts = thought + reasoning + plan

        prompt = ChatSequence.for_model(llm_model)
        prompt.add("user", feedback_prompt + feedback_thoughts)

        self.log_cycle_handler.log_cycle(
            self.config.ai_name,
            self.created_at,
            self.cycle_count,
            prompt.raw(),
            PROMPT_SUPERVISOR_FEEDBACK_FILE_NAME,
        )

        feedback = create_chat_completion(prompt)

        self.log_cycle_handler.log_cycle(
            self.config.ai_name,
            self.created_at,
            self.cycle_count,
            feedback,
            SUPERVISOR_FEEDBACK_FILE_NAME,
        )
</original>
<patched>
    def get_self_feedback(self, thoughts: dict, llm_model: str) -> str:
        """Generates a feedback response based on the provided thoughts dictionary.
        This method takes in a dictionary of thoughts containing keys such as 'reasoning',
        'plan', 'thoughts', and 'criticism'. It combines these elements into a single
        feedback message and uses the create_chat_completion() function to generate a
        response based on the input message.
        Args:
            thoughts (dict): A dictionary containing thought elements like reasoning,
            plan, thoughts, and criticism.
        Returns:
            str: A feedback response generated using the provided thoughts dictionary.
        """
        ai_role = self.config.ai_role

        feedback_prompt = f"Below is a message from me, an AI Agent, assuming the role of {ai_role}. whilst keeping knowledge of my slight limitations as an AI Agent Please evaluate my thought process, reasoning, and plan, and provide a concise paragraph outlining potential improvements. Consider adding or removing ideas that do not align with my role and explaining why, prioritizing thoughts based on their significance, or simply refining my overall thought process."
        reasoning = thoughts.get("reasoning", "")
        plan = thoughts.get("plan", "")
        thought = thoughts.get("thoughts", "")
        feedback_thoughts = thought + reasoning + plan

        prompt = ChatSequence.for_model(llm_model)
        prompt.add("user", feedback_prompt + feedback_thoughts)

        self.log_cycle_handler.log_cycle(
            self.config.ai_name,
            self.created_at,
            self.cycle_count,
            prompt.raw(),
            PROMPT_SUPERVISOR_FEEDBACK_FILE_NAME,
        )

        feedback = create_chat_completion(prompt, model=llm_model)

        self.log_cycle_handler.log_cycle(
            self.config.ai_name,
            self.created_at,
            self.cycle_count,
            feedback,
            SUPERVISOR_FEEDBACK_FILE_NAME,
        )
</patched>
```