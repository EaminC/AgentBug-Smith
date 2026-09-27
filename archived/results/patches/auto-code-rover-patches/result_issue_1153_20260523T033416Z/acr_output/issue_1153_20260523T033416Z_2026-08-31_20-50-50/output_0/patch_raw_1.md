Reasoning:
The issue describes that when using Azure, the deployment name provided by the user is mistakenly used as the "model_name" which conflicts with how AzureChatOpenAI expects the parameters: it requires `deployment_name` separate from `model_name`. Currently, the implementation uses `self.model_name` directly as the deployment name when constructing AzureChatOpenAI but does not distinguish between a model name and deployment_name. This causes the error where OpenAI API treats the deployment name as a model name.

The fix is:  
- When constructing the AzureChatOpenAI instance inside `_create_chat_model()` method, use a separate deployment name distinct from the model name for non-Azure usage.
- Modify the constructor of the AI class to take an optional `deployment_name` or re-purpose `model_name` to mean deployment_name if `azure_endpoint` is specified.
- For backward compatibility and simplicity, we can rename the parameter `model_name` in the AI constructor to `deployment_name` when azure is used, and store it separately inside the class.
- Then use the new attribute `deployment_name` in AzureChatOpenAI parameter `deployment_name`, and use a generic default `model_name` for the rest or for other providers.
- The change is minimal and impacts only how azure deployment and model name are used internally in AI class.
- The CLI invocation already passes the azure endpoint as a parameter and the deployment name as the model argument (which is confusing), so we just clarify internally and separate them.

This approach requires:  
- Change AI class constructor to receive both model_name and deployment_name separately, or interpret the single model_name parameter differently if azure is used. A clean, minimal method is to detect azure usage and store the value in a `self.deployment_name` variable while still keeping `self.model_name` as a model fallback.
- Modify the _create_chat_model method to use deployment_name parameter when using azure.

---

Patch:

# modification 1
```
<file>gpt_engineer/core/ai.py</file>
<original>    def __init__(
        self,
        model_name="gpt-4-turbo",
        temperature=0.1,
        azure_endpoint=None,
        streaming=True,
        vision=False,
    ):
        """
        Initialize the AI class.

        Parameters
        ----------
        model_name : str, optional
            The name of the model to use, by default "gpt-4".
        temperature : float, optional
            The temperature to use for the model, by default 0.1.
        """
        self.temperature = temperature
        self.azure_endpoint = azure_endpoint
        self.model_name = model_name
        self.streaming = streaming
        self.vision = (
            ("vision-preview" in model_name)
            or ("gpt-4-turbo" in model_name and "preview" not in model_name)
            or ("claude" in model_name)
        )
        self.llm = self._create_chat_model()
        self.token_usage_log = TokenUsageLog(model_name)

        logger.debug(f"Using model {self.model_name}")</original>
<patched>    def __init__(
        self,
        model_name="gpt-4-turbo",
        temperature=0.1,
        azure_endpoint=None,
        streaming=True,
        vision=False,
    ):
        """
        Initialize the AI class.

        Parameters
        ----------
        model_name : str, optional
            The name of the model to use or the Azure deployment name if using Azure, by default "gpt-4".
        temperature : float, optional
            The temperature to use for the model, by default 0.1.
        """
        self.temperature = temperature
        self.azure_endpoint = azure_endpoint

        # Distinguish deployment_name and model_name when azure_endpoint is set
        if azure_endpoint:
            self.deployment_name = model_name  # model_name from CLI is actually deployment_name for Azure
            # For Azure, model_name param to AzureChatOpenAI is None (will use deployment_name)
            self.model_name = None
        else:
            self.model_name = model_name
            self.deployment_name = None

        self.streaming = streaming
        self.vision = (
            (self.model_name and "vision-preview" in self.model_name)
            or (self.model_name and "gpt-4-turbo" in self.model_name and "preview" not in self.model_name)
            or (self.model_name and "claude" in self.model_name)
        )
        self.llm = self._create_chat_model()
        self.token_usage_log = TokenUsageLog(model_name)

        logger.debug(f"Using model {self.model_name or self.deployment_name}")</patched>
```

# modification 2
```
<file>gpt_engineer/core/ai.py</file>
<original>    def _create_chat_model(self) -> BaseChatModel:
        """
        Create a chat model with the specified model name and temperature.

        Parameters
        ----------
        model : str
            The name of the model to create.
        temperature : float
            The temperature to use for the model.

        Returns
        -------
        BaseChatModel
            The created chat model.
        """
        if self.azure_endpoint:
            return AzureChatOpenAI(
                azure_endpoint=self.azure_endpoint,
                openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
                deployment_name=self.model_name,
                openai_api_type="azure",
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
            )
        elif "claude" in self.model_name:
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                callbacks=[StreamingStdOutCallbackHandler()],
                streaming=self.streaming,
                max_tokens_to_sample=4096,
            )
        elif self.vision:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
                max_tokens=4096,  # vision models default to low max token limits
            )
        else:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
            )</original>
<patched>    def _create_chat_model(self) -> BaseChatModel:
        """
        Create a chat model with the specified model name and temperature.

        Parameters
        ----------
        model : str
            The name of the model to create.
        temperature : float
            The temperature to use for the model.

        Returns
        -------
        BaseChatModel
            The created chat model.
        """
        if self.azure_endpoint:
            return AzureChatOpenAI(
                azure_endpoint=self.azure_endpoint,
                openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
                deployment_name=self.deployment_name,
                openai_api_type="azure",
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
            )
        elif self.model_name and "claude" in self.model_name:
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                callbacks=[StreamingStdOutCallbackHandler()],
                streaming=self.streaming,
                max_tokens_to_sample=4096,
            )
        elif self.vision:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
                max_tokens=4096,  # vision models default to low max token limits
            )
        else:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                streaming=self.streaming,
                callbacks=[StreamingStdOutCallbackHandler()],
            )</patched>
```

Explanation:  
- We add `self.deployment_name` for Azure usage and use it explicitly in AzureChatOpenAI.  
- We leave `self.model_name` as None for Azure usage since the actual "model_name" is specified by the deployment name on Azure — the AzureChatOpenAI class expects a deployment_name parameter, not a model.  
- For other providers, use `self.model_name` unchanged.  
- We fix conditions to prevent errors if model_name is None (Azure case).  
- Logged model uses either model or deployment name to reflect what is actually used.

This minimal patch solves the bug described: the improper conflation of model_name and deployment_name for Azure deployments in gpt-engineer.