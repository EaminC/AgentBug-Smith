Reasoning:
The issue requests that both OpenAIModel and ClaudeModel support forwarding API URL changes. This means we should add an optional parameter for specifying a custom API base URL in the constructors of both classes. If the parameter is provided, it should be passed to the client initialization, otherwise fallback to the existing behavior.

For OpenAIModel, the OpenAI client accepts `api_key` and can also accept an optional `base_url` (or similar) parameter for API endpoint overrides.

For ClaudeModel, similarly, the Anthropic client can accept a `base_url` or `api_base` parameter to override the default endpoint.

Thus, the minimal change is to:
- Add an optional argument (named `api_url=None`) to both constructors.
- Pass it to the client initialization if provided.

No other changes are required as this will preserve existing behavior if the parameter is not passed.

---

Patch:

```
<file>mle/model.py</file>
<original>    def __init__(self, api_key, model, temperature=0.7):
        """
        Initialize the OpenAI model.
        Args:
            api_key (str): The OpenAI API key.
            model (str): The model with version.
            temperature (float): The temperature value.
        """
        super().__init__()

        dependency = "openai"
        spec = importlib.util.find_spec(dependency)
        if spec is not None:
            self.openai = importlib.import_module(dependency).OpenAI
        else:
            raise ImportError(
                "It seems you didn't install openai. In order to enable the OpenAI client related features, "
                "please make sure openai Python package has been installed. "
                "More information, please refer to: https://openai.com/product"
            )

        self.model = model if model else 'gpt-4o-2024-08-06'
        self.model_type = MODEL_OPENAI
        self.temperature = temperature
        self.client = self.openai(api_key=api_key)
        self.func_call_history = []
</original>
<patched>    def __init__(self, api_key, model, temperature=0.7, api_url=None):
        """
        Initialize the OpenAI model.
        Args:
            api_key (str): The OpenAI API key.
            model (str): The model with version.
            temperature (float): The temperature value.
            api_url (str, optional): Custom API base URL.
        """
        super().__init__()

        dependency = "openai"
        spec = importlib.util.find_spec(dependency)
        if spec is not None:
            self.openai = importlib.import_module(dependency).OpenAI
        else:
            raise ImportError(
                "It seems you didn't install openai. In order to enable the OpenAI client related features, "
                "please make sure openai Python package has been installed. "
                "More information, please refer to: https://openai.com/product"
            )

        self.model = model if model else 'gpt-4o-2024-08-06'
        self.model_type = MODEL_OPENAI
        self.temperature = temperature
        if api_url is not None:
            self.client = self.openai(api_key=api_key, base_url=api_url)
        else:
            self.client = self.openai(api_key=api_key)
        self.func_call_history = []
</patched>
</file>
```

```
<file>mle/model.py</file>
<original>    def __init__(self, api_key, model, temperature=0.7):
        """
        Initialize the Claude model.
        Args:
            api_key (str): The Anthropic API key.
            model (str): The model with version.
            temperature (float): The temperature value.
        """
        super().__init__()

        dependency = "anthropic"
        spec = importlib.util.find_spec(dependency)
        if spec is not None:
            self.anthropic = importlib.import_module(dependency).Anthropic
        else:
            raise ImportError(
                "It seems you didn't install anthropic. In order to enable the OpenAI client related features, "
                "please make sure openai Python package has been installed. "
                "More information, please refer to: https://docs.anthropic.com/en/api/client-sdks"
            )

        self.model = model if model else 'claude-3-5-sonnet-20240620'
        self.model_type = MODEL_CLAUDE
        self.temperature = temperature
        self.client = self.anthropic(api_key=api_key)
        self.func_call_history = []
</original>
<patched>    def __init__(self, api_key, model, temperature=0.7, api_url=None):
        """
        Initialize the Claude model.
        Args:
            api_key (str): The Anthropic API key.
            model (str): The model with version.
            temperature (float): The temperature value.
            api_url (str, optional): Custom API base URL.
        """
        super().__init__()

        dependency = "anthropic"
        spec = importlib.util.find_spec(dependency)
        if spec is not None:
            self.anthropic = importlib.import_module(dependency).Anthropic
        else:
            raise ImportError(
                "It seems you didn't install anthropic. In order to enable the OpenAI client related features, "
                "please make sure openai Python package has been installed. "
                "More information, please refer to: https://docs.anthropic.com/en/api/client-sdks"
            )

        self.model = model if model else 'claude-3-5-sonnet-20240620'
        self.model_type = MODEL_CLAUDE
        self.temperature = temperature
        if api_url is not None:
            self.client = self.anthropic(api_key=api_key, api_base=api_url)
        else:
            self.client = self.anthropic(api_key=api_key)
        self.func_call_history = []
</patched>
</file>
```