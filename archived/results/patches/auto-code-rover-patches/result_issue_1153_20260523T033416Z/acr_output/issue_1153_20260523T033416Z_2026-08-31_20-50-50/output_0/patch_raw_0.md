Reasoning:
The bug originates from confusion between the `model_name` and the `deployment_name` required for Azure OpenAI API calls. The user passes the Azure deployment name as `model_name` but in Azure OpenAI API usage, this should be set as the `deployment_name` parameter, and the actual model name should be set separately.

Currently, the AI class uses the single `model_name` attribute for both Azure deployment name and model name fields, causing Azure API to erroneously look for a model by the deployment name string, which fails.

To fix this with minimum disruption:
- Add an explicit `azure_deployment_name` argument to the AI constructor to separate the deployment name from model_name.
- Modify `_create_chat_model` to pass `deployment_name=azure_deployment_name`, and `model=model_name` as appropriate (note: AzureChatOpenAI class expects deployment_name but not model param).
- In the CLI `main` function, pass the `model` as GPT model name and `deployment_name` separately for Azure; since the user passes deployment name via the `--azure` option which is actually the endpoint, the deployment name should be passed as model (in existing code), so clarify this by adding a dedicated CLI option for deployment name or handle model name differently for Azure use (but minimal change preferred).
- For minimal change scope: add a new CLI option `--azure-deployment-name` to pass deployment name, and then in AI instantiation pass that to AI constructor separately from model name.

This patch:
- Extends AI class to accept `azure_deployment_name`.
- Modifies `_create_chat_model` to use `azure_deployment_name` as deployment_name in AzureChatOpenAI.
- Updates CLI `main()` to accept a new `--azure-deployment-name` argument and pass it along to AI.
- Keeps backward compatibility if `azure_deployment_name` is not provided (fallback to `model_name` as prior).

This ensures clear distinction between model_name (like "gpt-4-turbo") and Azure deployment name (like "gpt4turbo-dep") fixing the error.

---

Patch:

```
<file>gpt_engineer/core/ai.py</file>
<original>88     def __init__(
89         self,
90         model_name="gpt-4-turbo",
91         temperature=0.1,
92         azure_endpoint=None,
93         streaming=True,
94         vision=False,
95     ):
96         """
97         Initialize the AI class.
98 
99         Parameters
100         ----------
101         model_name : str, optional
102             The name of the model to use, by default "gpt-4".
103         temperature : float, optional
104             The temperature to use for the model, by default 0.1.
105         """
106         self.temperature = temperature
107         self.azure_endpoint = azure_endpoint
108         self.model_name = model_name
109         self.streaming = streaming
110         self.vision = (
111             ("vision-preview" in model_name)
112             or ("gpt-4-turbo" in model_name and "preview" not in model_name)
113             or ("claude" in model_name)
114         )
115         self.llm = self._create_chat_model()
116         self.token_usage_log = TokenUsageLog(model_name)
117 
118         logger.debug(f"Using model {self.model_name}")</original>
<patched>88     def __init__(
89         self,
90         model_name="gpt-4-turbo",
91         temperature=0.1,
92         azure_endpoint=None,
92a        azure_deployment_name=None,
93         streaming=True,
94         vision=False,
95     ):
96         """
97         Initialize the AI class.
98 
99         Parameters
100         ----------
101         model_name : str, optional
102             The name of the model to use, by default "gpt-4".
103         temperature : float, optional
104             The temperature to use for the model, by default 0.1.
105         azure_deployment_name : str, optional
106             The Azure OpenAI deployment name, if using Azure, by default None.
107         """
106a        self.temperature = temperature
107         self.azure_endpoint = azure_endpoint
107a        self.azure_deployment_name = azure_deployment_name
108         self.model_name = model_name
109         self.streaming = streaming
110         self.vision = (
111             ("vision-preview" in model_name)
112             or ("gpt-4-turbo" in model_name and "preview" not in model_name)
113             or ("claude" in model_name)
114         )
115         self.llm = self._create_chat_model()
116         self.token_usage_log = TokenUsageLog(model_name)
117 
118         logger.debug(f"Using model {self.model_name}")</patched>
</file>

<file>gpt_engineer/core/ai.py</file>
<original>330     def _create_chat_model(self) -> BaseChatModel:
331         """
332         Create a chat model with the specified model name and temperature.
333 
334         Parameters
335         ----------
336         model : str
337             The name of the model to create.
338         temperature : float
339             The temperature to use for the model.
340 
341         Returns
342         -------
343         BaseChatModel
344             The created chat model.
345         """
346         if self.azure_endpoint:
347             return AzureChatOpenAI(
348                 azure_endpoint=self.azure_endpoint,
349                 openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
350                 deployment_name=self.model_name,
351                 openai_api_type="azure",
352                 streaming=self.streaming,
353                 callbacks=[StreamingStdOutCallbackHandler()],
354             )
355         elif "claude" in self.model_name:
356             return ChatAnthropic(
357                 model=self.model_name,
358                 temperature=self.temperature,
359                 callbacks=[StreamingStdOutCallbackHandler()],
360                 streaming=self.streaming,
361                 max_tokens_to_sample=4096,
362             )
363         elif self.vision:
364             return ChatOpenAI(
365                 model=self.model_name,
366                 temperature=self.temperature,
367                 streaming=self.streaming,
368                 callbacks=[StreamingStdOutCallbackHandler()],
369                 max_tokens=4096,  # vision models default to low max token limits
370             )
371         else:
372             return ChatOpenAI(
373                 model=self.model_name,
374                 temperature=self.temperature,
375                 streaming=self.streaming,
376                 callbacks=[StreamingStdOutCallbackHandler()],
377             )
</original>
<patched>330     def _create_chat_model(self) -> BaseChatModel:
331         """
332         Create a chat model with the specified model name and temperature.
333 
334         Parameters
335         ----------
336         model : str
337             The name of the model to create.
338         temperature : float
339             The temperature to use for the model.
340 
341         Returns
342         -------
343         BaseChatModel
344             The created chat model.
345         """
346         if self.azure_endpoint:
347             # Use azure_deployment_name if provided, else fallback to model_name (legacy)
348             deployment_name = self.azure_deployment_name or self.model_name
349             return AzureChatOpenAI(
350                 azure_endpoint=self.azure_endpoint,
351                 openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
352                 deployment_name=deployment_name,
353                 openai_api_type="azure",
354                 streaming=self.streaming,
355                 callbacks=[StreamingStdOutCallbackHandler()],
356             )
357         elif "claude" in self.model_name:
358             return ChatAnthropic(
359                 model=self.model_name,
360                 temperature=self.temperature,
361                 callbacks=[StreamingStdOutCallbackHandler()],
362                 streaming=self.streaming,
363                 max_tokens_to_sample=4096,
364             )
365         elif self.vision:
366             return ChatOpenAI(
367                 model=self.model_name,
368                 temperature=self.temperature,
369                 streaming=self.streaming,
370                 callbacks=[StreamingStdOutCallbackHandler()],
371                 max_tokens=4096,  # vision models default to low max token limits
372             )
373         else:
374             return ChatOpenAI(
375                 model=self.model_name,
376                 temperature=self.temperature,
377                 streaming=self.streaming,
378                 callbacks=[StreamingStdOutCallbackHandler()],
379             )
</patched>
</file>

<file>gpt_engineer/applications/cli/main.py</file>
<original>283     azure_endpoint: str = typer.Option(
284         "",
285         "--azure",
286         "-a",
287         help="""Endpoint for your Azure OpenAI Service (https://xx.openai.azure.com).
288             In that case, the given model is the deployment name chosen in the Azure AI Studio.""",
289     ),
</original>
<patched>283     azure_endpoint: str = typer.Option(
284         "",
285         "--azure",
286         "-a",
287         help="""Endpoint for your Azure OpenAI Service (https://xx.openai.azure.com).
288             """,
289     ),
289a    azure_deployment_name: str = typer.Option(
289b        "",
289c        "--azure-deployment-name",
289d        help="Azure OpenAI deployment name (required if --azure endpoint is set).",
289e    ),
</patched>
</file>

<file>gpt_engineer/applications/cli/main.py</file>
<original>402         ai = AI(
403             model_name=model,
404             temperature=temperature,
405             azure_endpoint=azure_endpoint,
406         )
</original>
<patched>402         ai = AI(
403             model_name=model,
404             temperature=temperature,
405             azure_endpoint=azure_endpoint,
406             azure_deployment_name=azure_deployment_name if azure_deployment_name else None,
407         )
</patched>
</file>