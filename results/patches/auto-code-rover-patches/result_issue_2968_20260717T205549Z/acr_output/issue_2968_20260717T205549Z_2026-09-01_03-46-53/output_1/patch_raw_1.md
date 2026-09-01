```
<file>src/crewai/cli/create_crew.py</file>
<original>134 def create_crew(name, provider=None, skip_provider=False, parent_folder=None):
135     folder_path, folder_name, class_name = create_folder_structure(name, parent_folder)
136     env_vars = load_env_vars(folder_path)
137     if not skip_provider:
138         if not provider:
139             provider_models = get_provider_data()
140             if not provider_models:
141                 return
...
209             click.secho("API keys and model saved to .env file", fg="green")
210         else:
211             click.secho(
212                 "No API keys provided. Skipping .env file creation.", fg="yellow"
213             )
214 
215         click.secho(f"Selected model: {env_vars.get('MODEL', 'N/A')}", fg="green")
216 
217     package_dir = Path(__file__).parent
218     templates_dir = package_dir / "templates" / "crew"</original>
<patched>134 def create_crew(name, provider=None, skip_provider=False, parent_folder=None):
135     folder_path, folder_name, class_name = create_folder_structure(name, parent_folder)
136     env_vars = load_env_vars(folder_path)
136.1    import os
136.2    # Set loaded environment variables in runtime environment for OpenAI client and others
136.3    for key, value in env_vars.items():
136.4        os.environ[key] = value
137     if not skip_provider:
138         if not provider:
139             provider_models = get_provider_data()
140             if not provider_models:
141                 return
...
209             click.secho("API keys and model saved to .env file", fg="green")
210         else:
211             click.secho(
212                 "No API keys provided. Skipping .env file creation.", fg="yellow"
213             )
214 
215         click.secho(f"Selected model: {env_vars.get('MODEL', 'N/A')}", fg="green")
216 
217     package_dir = Path(__file__).parent
218     templates_dir = package_dir / "templates" / "crew"</patched>
```