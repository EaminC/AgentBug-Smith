```
<file>src/crewai/llm.py</file>
<original>
60 load_dotenv()


class FilteredStream(io.TextIOBase):
</original>
<patched>
60 load_dotenv()

import os

def _set_azure_env_vars_to_openai():
    """
    Helper to map Azure-specific environment variables to OpenAI expected variables if using Azure.
    This ensures the API key client option is set correctly from AZURE_API_KEY before client usage.
    """
    azure_api_key = os.getenv("AZURE_API_KEY")
    if azure_api_key and not os.getenv("OPENAI_API_KEY"):
        # Set OPENAI_API_KEY env var so the OpenAI client picks it up
        os.environ["OPENAI_API_KEY"] = azure_api_key

# Ensure environment variables for Azure API keys are mapped appropriately early
_set_azure_env_vars_to_openai()


class FilteredStream(io.TextIOBase):
</patched>
```

```
<file>src/crewai/cli/create_crew.py</file>
<original>
136     env_vars = load_env_vars(folder_path)
137     if not skip_provider:
138         if not provider:
139             provider_models = get_provider_data()
140             if not provider_models:
141                 return
...
207         if env_vars:
208             write_env_file(folder_path, env_vars)
209             click.secho("API keys and model saved to .env file", fg="green")
210         else:
211             click.secho(
212                 "No API keys provided. Skipping .env file creation.", fg="yellow"
213             )
</original>
<patched>
136     env_vars = load_env_vars(folder_path)
137     if not skip_provider:
138         if not provider:
139             provider_models = get_provider_data()
140             if not provider_models:
141                 return
...
207         if env_vars:
208             write_env_file(folder_path, env_vars)
209             click.secho("API keys and model saved to .env file", fg="green")
210
211             # Immediately reload environment variables from .env
212             load_dotenv(dotenv_path=folder_path / ".env", override=True)
213
214             # Also explicitly set AZURE_API_KEY as environment variable for runtime usage
215             azure_key = env_vars.get("AZURE_API_KEY")
216             if azure_key:
217                 os.environ["AZURE_API_KEY"] = azure_key
218
219             # Sync with OPENAI_API_KEY if Azure is used to avoid client missing key error
220             if "AZURE_API_KEY" in env_vars and not os.getenv("OPENAI_API_KEY"):
221                 os.environ["OPENAI_API_KEY"] = env_vars["AZURE_API_KEY"]
222
223         else:
224             click.secho(
225                 "No API keys provided. Skipping .env file creation.", fg="yellow"
226             )
</patched>
```