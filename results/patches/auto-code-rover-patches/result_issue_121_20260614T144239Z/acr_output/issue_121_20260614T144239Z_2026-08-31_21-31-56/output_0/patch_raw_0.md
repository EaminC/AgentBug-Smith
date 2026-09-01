Reasoning:
The user asks for a way to restart a previous session in the baseline workflow. The current baseline implementation does not provide a way to save and restore session progress.

To address this:
1. Add session save/load functionality in the `baseline` workflow, so that the dataset info, user requirement, advisor report, coding plan, and task progress (including code and debug states) can be saved and resumed.
2. Add methods to `CodeAgent` and `DebugAgent` to serialize (save) and load their internal state such as chat history, code summary, and debug chat history.
3. Update `cli.py` start function to optionally accept a `--resume` flag to resume the previous session.
4. Use a fixed session state file name, e.g., `.mle_session.json` inside the working directory, to save/load the session state.

This minimal patch adds session persistence and recovery without breaking the fresh start baseline flow.

---

Patch:

```
<file>mle/workflow/baseline.py</file>
<original>def baseline(work_dir: str, model='gpt-4o'):
    """
    The workflow of the baseline mode.
    :return:
    """

    console = Console()
    model = load_model(work_dir, model)

    # ask for the data information
    dataset = ask_text("Please provide your dataset information (a public dataset name or a local file path)")
    if not dataset:
        print_in_box("The dataset is empty. Aborted", console, title="Error", color="red")
        return

    # ask for the user requirement
    ml_requirement = ask_text("Please provide the user requirement")
    if not ml_requirement:
        print_in_box("The user's requirement is empty. Aborted", console, title="Error", color="red")
        return

    # advisor agent gives suggestions in a report
    advisor = AdviseAgent(model, console)
    advisor_report = advisor.interact("[green]User Requirement:[/green] " + ml_requirement + "\n" + ask_data(dataset))

    # plan agent generates the coding plan
    planner = PlanAgent(model, console)
    coding_plan = planner.interact(advisor_report)

    # code agent codes the tasks and debug with the debug agent
    coder = CodeAgent(model, work_dir, console)
    coder.read_requirement(advisor_report)
    debugger = DebugAgent(model, console)

    is_auto_mode = questionary.confirm(
        "MLE developer is about to start to code.\n"
        "Choose to debug or not (If no, MLE agent will only focus on coding tasks,"
        " and you have to run and debug the code yourself)?"
    ).ask()

    for current_task in coding_plan.get('tasks'):
        code_report = coder.interact(current_task)
        is_debugging = code_report.get('debug')

        if is_auto_mode:
            while True:
                if is_debugging == 'true' or is_debugging == 'True':
                    with console.status("Debugger is executing and debugging the code..."):
                        debug_report = debugger.analyze(code_report)
                    if debug_report.get('status') == 'success':
                        break
                    else:
                        code_report = coder.debug(current_task, debug_report)
                else:
                    break
</original>
<patched>import json
import os

def baseline(work_dir: str, model='gpt-4o', resume=False):
    """
    The workflow of the baseline mode with optional resume support.
    :return:
    """

    console = Console()
    model = load_model(work_dir, model)

    session_file = os.path.join(work_dir, '.mle_session.json')

    if resume and os.path.exists(session_file):
        # Load session state
        with open(session_file, 'r') as f:
            session_data = json.load(f)

        dataset = session_data.get('dataset')
        ml_requirement = session_data.get('ml_requirement')
        advisor_report = session_data.get('advisor_report')
        coding_plan = session_data.get('coding_plan')
        task_index = session_data.get('task_index', 0)
    else:
        # ask for the data information
        dataset = ask_text("Please provide your dataset information (a public dataset name or a local file path)")
        if not dataset:
            print_in_box("The dataset is empty. Aborted", console, title="Error", color="red")
            return

        # ask for the user requirement
        ml_requirement = ask_text("Please provide the user requirement")
        if not ml_requirement:
            print_in_box("The user's requirement is empty. Aborted", console, title="Error", color="red")
            return

        # advisor agent gives suggestions in a report
        advisor = AdviseAgent(model, console)
        advisor_report = advisor.interact("[green]User Requirement:[/green] " + ml_requirement + "\n" + ask_data(dataset))

        # plan agent generates the coding plan
        planner = PlanAgent(model, console)
        coding_plan = planner.interact(advisor_report)

        task_index = 0

    # Prepare agents
    coder = CodeAgent(model, work_dir, console)
    coder.read_requirement(advisor_report)
    debugger = DebugAgent(model, console)

    # If resuming, load internal agent states
    if resume and os.path.exists(session_file):
        # Load coder state if any
        coder_state = session_data.get('coder_state')
        if coder_state:
            coder.load_state(coder_state)
        # Load debugger state if any
        debugger_state = session_data.get('debugger_state')
        if debugger_state:
            debugger.load_state(debugger_state)

    is_auto_mode = questionary.confirm(
        "MLE developer is about to start to code.\n"
        "Choose to debug or not (If no, MLE agent will only focus on coding tasks,"
        " and you have to run and debug the code yourself)?"
    ).ask()

    tasks = coding_plan.get('tasks', [])
    for i in range(task_index, len(tasks)):
        current_task = tasks[i]
        code_report = coder.interact(current_task)
        is_debugging = code_report.get('debug')

        if is_auto_mode:
            while True:
                if is_debugging == 'true' or is_debugging == 'True':
                    with console.status("Debugger is executing and debugging the code..."):
                        debug_report = debugger.analyze(code_report)
                    if debug_report.get('status') == 'success':
                        break
                    else:
                        code_report = coder.debug(current_task, debug_report)
                else:
                    break

        # Save session state after each task
        session_data = {
            'dataset': dataset,
            'ml_requirement': ml_requirement,
            'advisor_report': advisor_report,
            'coding_plan': coding_plan,
            'task_index': i + 1,
            'coder_state': coder.save_state(),
            'debugger_state': debugger.save_state()
        }
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

    # On completion remove session file
    if os.path.exists(session_file):
        os.remove(session_file)
</patched>
```

```
<file>mle/agents/coder.py</file>
<original>class CodeAgent:

    def __init__(self, model, working_dir='.', console=None):
        ...
        self.chat_history = []
        self.working_dir = working_dir
        ...
        self.code_summary = None
        ...
    def interact(self, task_dict: dict):
        ...
        self.code_summary = self.code(task_dict)
        print_in_box(process_summary(self.code_summary), self.console, title="MLE Developer", color="cyan")
        while True:
            suggestion = questionary.text(
                "Any feedback to MLE developer? (ENTER to move to the next stage, \"exit\" to exit the project)"
            ).ask()

            if not suggestion:
                break

            if suggestion.lower() in ["exit"]:
                sys.exit(0)

            with self.console.status(f"MLE Developer is working on the task: {task_dict.get('task')}..."):
                self.chat_history.append({"role": "user", "content": suggestion})
                text = self.model.query(
                    self.chat_history,
                    function_call='auto',
                    functions=self.functions,
                    response_format={"type": "json_object"}
                )

                self.chat_history.append({"role": "assistant", "content": text})
                self.code_summary = json.loads(text)
                self.code_summary.update(
                    {
                        'task': task_dict.get('task'),
                        'task_description': task_dict.get('description')
                    }
                )
            print_in_box(process_summary(self.code_summary), self.console, title="MLE Developer", color="cyan")
        return self.code_summary
</original>
<patched>import json

class CodeAgent:

    def __init__(self, model, working_dir='.', console=None):
        ...
        self.chat_history = []
        self.working_dir = working_dir
        ...
        self.code_summary = None
        ...
    def save_state(self):
        """
        Save internal state for resuming session.
        Returns a dict to be serialized.
        """
        return {
            'chat_history': self.chat_history,
            'code_summary': self.code_summary
        }

    def load_state(self, state: dict):
        """
        Load internal state from saved dict.
        """
        if not state:
            return
        self.chat_history = state.get('chat_history', [])
        self.code_summary = state.get('code_summary')

    def interact(self, task_dict: dict):
        ...
        self.code_summary = self.code(task_dict)
        print_in_box(process_summary(self.code_summary), self.console, title="MLE Developer", color="cyan")
        while True:
            suggestion = questionary.text(
                "Any feedback to MLE developer? (ENTER to move to the next stage, \"exit\" to exit the project)"
            ).ask()

            if not suggestion:
                break

            if suggestion.lower() in ["exit"]:
                sys.exit(0)

            with self.console.status(f"MLE Developer is working on the task: {task_dict.get('task')}..."):
                self.chat_history.append({"role": "user", "content": suggestion})
                text = self.model.query(
                    self.chat_history,
                    function_call='auto',
                    functions=self.functions,
                    response_format={"type": "json_object"}
                )

                self.chat_history.append({"role": "assistant", "content": text})
                self.code_summary = json.loads(text)
                self.code_summary.update(
                    {
                        'task': task_dict.get('task'),
                        'task_description': task_dict.get('description')
                    }
                )
            print_in_box(process_summary(self.code_summary), self.console, title="MLE Developer", color="cyan")
        return self.code_summary
</patched>
```

```
<file>mle/agents/debugger.py</file>
<original>class DebugAgent:

    def __init__(self, model, console=None):
        ...
        self.chat_history = []
        ...
    def analyze(self, code_report):
        ...
        self.chat_history.append({"role": "user", "content": debug_prompt})
        text = self.model.query(
            self.chat_history,
            function_call='auto',
            functions=self.functions,
            response_format={"type": "json_object"}
        )

        self.chat_history.append({"role": "assistant", "content": text})
        report_dict = json.loads(text)
        print_in_box(process_debug_report(report_dict), self.console, title="MLE Debugger", color="yellow")
        return report_dict
</original>
<patched>import json

class DebugAgent:

    def __init__(self, model, console=None):
        ...
        self.chat_history = []
        ...
    def save_state(self):
        """
        Save internal state for resuming session.
        """
        return {
            'chat_history': self.chat_history
        }

    def load_state(self, state: dict):
        """
        Load internal state from saved dict.
        """
        if not state:
            return
        self.chat_history = state.get('chat_history', [])

    def analyze(self, code_report):
        ...
        self.chat_history.append({"role": "user", "content": debug_prompt})
        text = self.model.query(
            self.chat_history,
            function_call='auto',
            functions=self.functions,
            response_format={"type": "json_object"}
        )

        self.chat_history.append({"role": "assistant", "content": text})
        report_dict = json.loads(text)
        print_in_box(process_debug_report(report_dict), self.console, title="MLE Debugger", color="yellow")
        return report_dict
</patched>
```

```
<file>mle/cli.py</file>
<original>def start(mode, model):
    """
    start: start the chat with LLM.
    """
    if not check_config():
        return

    if mode == 'kaggle':
        # Kaggle mode
        console.log("Kaggle mode is not supported yet. Aborted.")
        return kaggle(os.getcwd(), model)
    else:
        # Baseline mode
        return baseline(os.getcwd(), model)
</original>
<patched>import argparse

def start(mode, model, resume=False):
    """
    start: start the chat with LLM.
    """
    if not check_config():
        return

    if mode == 'kaggle':
        # Kaggle mode
        console.log("Kaggle mode is not supported yet. Aborted.")
        return kaggle(os.getcwd(), model)
    else:
        # Baseline mode
        # Pass resume flag to baseline
        return baseline(os.getcwd(), model, resume=resume)
</patched>
```