Reasoning:
The issue requests to enhance the project planning display by showing it as a DAG or table to improve understandability. The main logic for planning is inside `plan_agent.py`, where the plan generation and detailed description generation occur. The current plan data structure is a list of tasks with names and descriptions, but no visual display function exists.

Steps to resolve:
1. Add a new function `display_plan_as_dag` inside `agent/function/plan_agent.py` that uses `rich` library (already partially used) to render the plan as a DAG-like tree or table.
2. This function will take the plan tasks and visually represent the steps and dependencies (or a simple DAG/tree if no explicit dependencies).
3. Modify `agent/function/tech_leader.py` inside the `LeaderAgent.start` method to invoke this new display method after plan generation is confirmed.
4. This keeps existing flow intact but adds the visual plan display after the plan generated and confirmed.

No changes are needed anywhere else, imports and usage of `rich` is already available in `plan_agent.py` and `tech_leader.py`.

---

Patch:

```
<file>agent/function/plan_agent.py</file>
<original>168 def plan_generator(
169         requirement: str,
170         llm_agent,
171 ):
172     """
173     Generate the project plan based on the user's requirements.
174     :param requirement: the user's requirements.
175     :param llm_agent: the language model agent.
176     :return: the project plan.
177     """
178     task_list = []
179     for task in load_yml('plan.yml'):
180         task_list.append(
181             {
182                 'name': task['name'],
183                 'prompt': task['prompt'],
184                 'resources': [r['name'] for r in task.get('resources')]
185             }
186         )
187     chat_history = [
188         {"role": 'system', "content": pmpt_plan(json.dumps(task_list))},
189         {"role": 'user', "content": requirement}
190     ]
191     target_tasks = llm_agent.query(chat_history)
192 
193     # generate the completed plan with detailed description
194     return description_generator(requirement, target_tasks, llm_agent)
</original>
<patched>168 def plan_generator(
169         requirement: str,
170         llm_agent,
171 ):
172     """
173     Generate the project plan based on the user's requirements.
174     :param requirement: the user's requirements.
175     :param llm_agent: the language model agent.
176     :return: the project plan.
177     """
178     task_list = []
179     for task in load_yml('plan.yml'):
180         task_list.append(
181             {
182                 'name': task['name'],
183                 'prompt': task['prompt'],
184                 'resources': [r['name'] for r in task.get('resources')]
185             }
186         )
187     chat_history = [
188         {"role": 'system', "content": pmpt_plan(json.dumps(task_list))},
189         {"role": 'user', "content": requirement}
190     ]
191     target_tasks = llm_agent.query(chat_history)
192 
193     # generate the completed plan with detailed description
194     return description_generator(requirement, target_tasks, llm_agent)
195 
196 
197 from rich.tree import Tree
198 from rich.table import Table
199 
200 def display_plan_as_dag(plan_tasks, console=None):
201     """
202     Display the project plan as a DAG-like tree to enhance understandability.
203     :param plan_tasks: list of task dicts with 'name' and optionally 'dependencies' keys.
204     :param console: rich.console.Console instance or None to create one.
205     """
206     if console is None:
207         console = Console()
208 
209     # Simple DAG display as a tree assuming tasks sequentially; no explicit dependency relations currently
210     tree = Tree("[bold blue]Project Plan[/bold blue]")
211     for i, task in enumerate(plan_tasks):
212         task_name = task.get('name', f"Task {i+1}")
213         # add task description if available
214         description = task.get('description') or task.get('desc') or ""
215         if description:
216             subtree = tree.add(f"[green]{task_name}[/green]: {description}")
217         else:
218             subtree = tree.add(f"[green]{task_name}[/green]")
219         # If resources are present, list them as children
220         resources = task.get('resources')
221         if resources:
222             resources_node = subtree.add("[yellow]Resources[/yellow]")
223             for res in resources:
224                 resources_node.add(f"[yellow]{res}[/yellow]")
225 
226     console.print(tree)
227 
228     # Alternatively, also show the plan as a Table for clarity
229     table = Table(title="Project Plan Tasks")
230     table.add_column("Step", style="cyan", no_wrap=True)
231     table.add_column("Task Name", style="magenta")
232     table.add_column("Description", style="green")
233 
234     for idx, task in enumerate(plan_tasks, start=1):
235         name = task.get('name', '')
236         desc = task.get('description') or task.get('desc') or ''
237         table.add_row(str(idx), name, desc)
238 
239     console.print(table)
</patched>
```

---

```
<file>agent/function/tech_leader.py</file>
<original>142                 if self.project.plan.tasks is None:
143                     self.console.log("[bold red]Step 4: Plan generation[bold red]")
144                     self.console.log(
145                         f"The project [cyan]{self.project.name}[/cyan] has no existing plans. Start planning..."
146                     )
147                     self.requirement += f"\n\nDataset: {self.project.plan.dataset}"
148                     with self.console.status("Planning the tasks for you..."):
149                         task_dicts = plan_generator(
150                             self.requirement,
151                             self.model,
152                         )
153                         self.console.log(task_dicts)
154                         self.project.plan.tasks = []
155                         for task_dict in task_dicts.get('tasks'):
156                             task = match_plan(task_dict)
157                             if task:
158                                 self.project.plan.tasks.append(task)
159 
160                     # Confirm the plan
161                     confirm_plan = questionary.confirm("Are you sure to use this plan?").ask()
162                     if confirm_plan:
163                         update_project_state(self.project)
164                     else:
165                         self.console.log("Seems you are not satisfied with the plan. Aborting the chain.")
166                         return
</original>
<patched>142                 if self.project.plan.tasks is None:
143                     self.console.log("[bold red]Step 4: Plan generation[bold red]")
144                     self.console.log(
145                         f"The project [cyan]{self.project.name}[/cyan] has no existing plans. Start planning..."
146                     )
147                     self.requirement += f"\n\nDataset: {self.project.plan.dataset}"
148                     with self.console.status("Planning the tasks for you..."):
149                         task_dicts = plan_generator(
150                             self.requirement,
151                             self.model,
152                         )
153                         self.console.log(task_dicts)
154                         self.project.plan.tasks = []
155                         for task_dict in task_dicts.get('tasks'):
156                             task = match_plan(task_dict)
157                             if task:
158                                 self.project.plan.tasks.append(task)
159 
160                     # Confirm the plan
161                     confirm_plan = questionary.confirm("Are you sure to use this plan?").ask()
162                     if confirm_plan:
163                         update_project_state(self.project)
164                         # Display the plan visually as a DAG and Table
165                         from agent.function.plan_agent import display_plan_as_dag
166                         display_plan_as_dag(self.project.plan.tasks, self.console)
167                     else:
168                         self.console.log("Seems you are not satisfied with the plan. Aborting the chain.")
169                         return
</patched>
```