```
<file>src/crewai/cli/create_crew.py</file>
<original>
134 def create_crew(name, provider=None, skip_provider=False, parent_folder=None):
135     folder_path, folder_name, class_name = create_folder_structure(name, parent_folder)
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
214 
215         click.secho(f"Selected model: {env_vars.get('MODEL', 'N/A')}", fg="green")
216 
217     package_dir = Path(__file__).parent
218     templates_dir = package_dir / "templates" / "crew"
219 
220     root_template_files = (
221         [".gitignore", "pyproject.toml", "README.md", "knowledge/user_preference.txt"]
222         if not parent_folder
223         else []
224     )
225     tools_template_files = ["tools/custom_tool.py", "tools/__init__.py"]
226     config_template_files = ["config/agents.yaml", "config/tasks.yaml"]
227     src_template_files = (
228         ["__init__.py", "main.py", "crew.py"] if not parent_folder else ["crew.py"]
229     )
230 
231     for file_name in root_template_files:
232         src_file = templates_dir / file_name
233         dst_file = folder_path / file_name
234         copy_template(src_file, dst_file, name, class_name, folder_name)
235 
236     src_folder = folder_path / "src" / folder_name if not parent_folder else folder_path
237 
238     for file_name in src_template_files:
239         src_file = templates_dir / file_name
240         dst_file = src_folder / file_name
241         copy_template(src_file, dst_file, name, class_name, folder_name)
242 
243     if not parent_folder:
244         for file_name in tools_template_files + config_template_files:
245             src_file = templates_dir / file_name
246             dst_file = src_folder / file_name
247             copy_template(src_file, dst_file, name, class_name, folder_name)
248 
249     click.secho(f"Crew {name} created successfully!", fg="green", bold=True)
</original>
<patched>
134 def create_crew(name, provider=None, skip_provider=False, parent_folder=None):
135     import os
136     folder_path, folder_name, class_name = create_folder_structure(name, parent_folder)
137     env_vars = load_env_vars(folder_path)
138     # Set loaded env vars into os.environ to ensure they are available at runtime
139     for key, value in env_vars.items():
140         os.environ[key] = value
141 
142     if not skip_provider:
143         if not provider:
144             provider_models = get_provider_data()
145             if not provider_models:
146                 return
147 
148         existing_provider = None
149         for provider, env_keys in ENV_VARS.items():
150             if any(
151                 "key_name" in details and details["key_name"] in env_vars
152                 for details in env_keys
153             ):
154                 existing_provider = provider
155                 break
156 
157         if existing_provider:
158             if not click.confirm(
159                 f"Found existing environment variable configuration for {existing_provider.capitalize()}. Do you want to override it?"
160             ):
161                 click.secho("Keeping existing provider configuration.", fg="yellow")
162                 return
163 
164         provider_models = get_provider_data()
165         if not provider_models:
166             return
167 
168         while True:
169             selected_provider = select_provider(provider_models)
170             if selected_provider is None:  # User typed 'q'
171                 click.secho("Exiting...", fg="yellow")
172                 sys.exit(0)
173             if selected_provider:  # Valid selection
174                 break
175             click.secho(
176                 "No provider selected. Please try again or press 'q' to exit.", fg="red"
177             )
178 
179         # Check if the selected provider has predefined models
180         if selected_provider in MODELS and MODELS[selected_provider]:
181             while True:
182                 selected_model = select_model(selected_provider, provider_models)
183                 if selected_model is None:  # User typed 'q'
184                     click.secho("Exiting...", fg="yellow")
185                     sys.exit(0)
186                 if selected_model:  # Valid selection
187                     break
188                 click.secho(
189                     "No model selected. Please try again or press 'q' to exit.",
190                     fg="red",
191                 )
192             env_vars["MODEL"] = selected_model
193 
194         # Check if the selected provider requires API keys
195         if selected_provider in ENV_VARS:
196             provider_env_vars = ENV_VARS[selected_provider]
197             for details in provider_env_vars:
198                 if details.get("default", False):
199                     # Automatically add default key-value pairs
200                     for key, value in details.items():
201                         if key not in ["prompt", "key_name", "default"]:
202                             env_vars[key] = value
203                 elif "key_name" in details:
204                     # Prompt for non-default key-value pairs
205                     prompt = details["prompt"]
206                     key_name = details["key_name"]
207                     api_key_value = click.prompt(prompt, default="", show_default=False)
208 
209                     if api_key_value.strip():
210                         env_vars[key_name] = api_key_value
211 
212         if env_vars:
213             write_env_file(folder_path, env_vars)
214             click.secho("API keys and model saved to .env file", fg="green")
215             # Also update os.environ after writing .env
216             for key, value in env_vars.items():
217                 os.environ[key] = value
218         else:
219             click.secho(
220                 "No API keys provided. Skipping .env file creation.", fg="yellow"
221             )
222 
223         click.secho(f"Selected model: {env_vars.get('MODEL', 'N/A')}", fg="green")
224 
225     package_dir = Path(__file__).parent
226     templates_dir = package_dir / "templates" / "crew"
227 
228     root_template_files = (
229         [".gitignore", "pyproject.toml", "README.md", "knowledge/user_preference.txt"]
230         if not parent_folder
231         else []
232     )
233     tools_template_files = ["tools/custom_tool.py", "tools/__init__.py"]
234     config_template_files = ["config/agents.yaml", "config/tasks.yaml"]
235     src_template_files = (
236         ["__init__.py", "main.py", "crew.py"] if not parent_folder else ["crew.py"]
237     )
238 
239     for file_name in root_template_files:
240         src_file = templates_dir / file_name
241         dst_file = folder_path / file_name
242         copy_template(src_file, dst_file, name, class_name, folder_name)
243 
244     src_folder = folder_path / "src" / folder_name if not parent_folder else folder_path
245 
246     for file_name in src_template_files:
247         src_file = templates_dir / file_name
248         dst_file = src_folder / file_name
249         copy_template(src_file, dst_file, name, class_name, folder_name)
250 
251     if not parent_folder:
252         for file_name in tools_template_files + config_template_files:
253             src_file = templates_dir / file_name
254             dst_file = src_folder / file_name
255             copy_template(src_file, dst_file, name, class_name, folder_name)
256 
257     click.secho(f"Crew {name} created successfully!", fg="green", bold=True)
</patched>
```