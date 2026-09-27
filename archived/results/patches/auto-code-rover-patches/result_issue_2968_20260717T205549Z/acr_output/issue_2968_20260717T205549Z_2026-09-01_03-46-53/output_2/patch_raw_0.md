```
<file>src/crewai/llm.py</file>
<original>
22 from dotenv import load_dotenv
...
60 load_dotenv()
</original>
<patched>
22 from dotenv import load_dotenv
import os
...
60 load_dotenv()

61 # Map Azure environment variables to OpenAI expected environment variables if running with Azure config
62 if "AZURE_API_KEY" in os.environ:
63     # Set OPENAI_API_KEY to AZURE_API_KEY so OpenAI client initializes correctly
64     os.environ.setdefault("OPENAI_API_KEY", os.environ["AZURE_API_KEY"])
65 if "AZURE_API_BASE" in os.environ:
66     os.environ.setdefault("OPENAI_API_BASE", os.environ["AZURE_API_BASE"])
67 if "AZURE_API_VERSION" in os.environ:
68     os.environ.setdefault("OPENAI_API_VERSION", os.environ["AZURE_API_VERSION"])
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
142 
143         existing_provider = None
144         for provider, env_keys in ENV_VARS.items():
145             if any(
146                 "key_name" in details and details["key_name"] in env_vars
147                 for details in env_keys
148             ):
149                 existing_provider = provider
150                 break
151 
152         if existing_provider:
153             if not click.confirm(
154                 f"Found existing environment variable configuration for {existing_provider.capitalize()}. Do you want to override it?"
155             ):
156                 click.secho("Keeping existing provider configuration.", fg="yellow")
157                 return
158 
159         provider_models = get_provider_data()
160         if not provider_models:
161             return
162 
163         while True:
164             selected_provider = select_provider(provider_models)
165             if selected_provider is None:  # User typed 'q'
166                 click.secho("Exiting...", fg="yellow")
167                 sys.exit(0)
168             if selected_provider:  # Valid selection
169                 break
170             click.secho(
171                 "No provider selected. Please try again or press 'q' to exit.", fg="red"
172             )
173 
174         # Check if the selected provider has predefined models
175         if selected_provider in MODELS and MODELS[selected_provider]:
176             while True:
177                 selected_model = select_model(selected_provider, provider_models)
178                 if selected_model is None:  # User typed 'q'
179                     click.secho("Exiting...", fg="yellow")
180                     sys.exit(0)
181                 if selected_model:  # Valid selection
182                     break
183                 click.secho(
184                     "No model selected. Please try again or press 'q' to exit.",
185                     fg="red",
186                 )
187             env_vars["MODEL"] = selected_model
188 
189         # Check if the selected provider requires API keys
190         if selected_provider in ENV_VARS:
191             provider_env_vars = ENV_VARS[selected_provider]
192             for details in provider_env_vars:
193                 if details.get("default", False):
194                     # Automatically add default key-value pairs
195                     for key, value in details.items():
196                         if key not in ["prompt", "key_name", "default"]:
197                             env_vars[key] = value
198                 elif "key_name" in details:
199                     # Prompt for non-default key-value pairs
200                     prompt = details["prompt"]
201                     key_name = details["key_name"]
202                     api_key_value = click.prompt(prompt, default="", show_default=False)
203 
204                     if api_key_value.strip():
205                         env_vars[key_name] = api_key_value
206 
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
142 
143         existing_provider = None
144         for provider, env_keys in ENV_VARS.items():
145             if any(
146                 "key_name" in details and details["key_name"] in env_vars
147                 for details in env_keys
148             ):
149                 existing_provider = provider
150                 break
151 
152         if existing_provider:
153             if not click.confirm(
154                 f"Found existing environment variable configuration for {existing_provider.capitalize()}. Do you want to override it?"
155             ):
156                 click.secho("Keeping existing provider configuration.", fg="yellow")
157                 return
158 
159         provider_models = get_provider_data()
160         if not provider_models:
161             return
162 
163         while True:
164             selected_provider = select_provider(provider_models)
165             if selected_provider is None:  # User typed 'q'
166                 click.secho("Exiting...", fg="yellow")
167                 sys.exit(0)
168             if selected_provider:  # Valid selection
169                 break
170             click.secho(
171                 "No provider selected. Please try again or press 'q' to exit.", fg="red"
172             )
173 
174         # Check if the selected provider has predefined models
175         if selected_provider in MODELS and MODELS[selected_provider]:
176             while True:
177                 selected_model = select_model(selected_provider, provider_models)
178                 if selected_model is None:  # User typed 'q'
179                     click.secho("Exiting...", fg="yellow")
180                     sys.exit(0)
181                 if selected_model:  # Valid selection
182                     break
183                 click.secho(
184                     "No model selected. Please try again or press 'q' to exit.",
185                     fg="red",
186                 )
187             env_vars["MODEL"] = selected_model
188 
189         # Check if the selected provider requires API keys
190         if selected_provider in ENV_VARS:
191             provider_env_vars = ENV_VARS[selected_provider]
192             for details in provider_env_vars:
193                 if details.get("default", False):
194                     # Automatically add default key-value pairs
195                     for key, value in details.items():
196                         if key not in ["prompt", "key_name", "default"]:
197                             env_vars[key] = value
198                 elif "key_name" in details:
199                     # Prompt for non-default key-value pairs
200                     prompt = details["prompt"]
201                     key_name = details["key_name"]
202                     api_key_value = click.prompt(prompt, default="", show_default=False)
203 
204                     if api_key_value.strip():
205                         env_vars[key_name] = api_key_value
206 
207         if env_vars:
208             write_env_file(folder_path, env_vars)
209             click.secho("API keys and model saved to .env file", fg="green")
210             
211             # After saving .env, reload environment variables into os.environ for immediate use
212             from dotenv import load_dotenv
213             load_dotenv(dotenv_path=folder_path / ".env", override=True)
214         else:
215             click.secho(
216                 "No API keys provided. Skipping .env file creation.", fg="yellow"
217             )
</patched>
```