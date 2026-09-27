The issue requests combining the `pnpm dev` command (which runs the frontend development server) and the `mle serve` CLI to start the backend FastAPI server into a single CLI command `mle report`.

Currently, `report` command either builds a new local project or runs the report workflow in the current directory, but does not start any frontend development server or backend FastAPI server as part of the `report` command.

The intended behavior is to:  
- Before the current report workflow runs, start `pnpm dev` (frontend) using the existing utility `execute_command` (which should run shell commands and output logs).  
- Then start the backend FastAPI server via the existing `serve` method invoked via `ctx.invoke(serve, ...)`.  
- Finally, run the current report generation workflow.

This requires importing `execute_command` and `serve`.  
We need to add the `execute_command(['pnpm', 'dev'])` call and ensure that `serve` is invoked after that with the parameters from current context or hardcoded as necessary.  
We want to preserve current functionality otherwise and provide clear information.

The minimal patch involves adding imports and inserting the commands just before calling `workflow.report`. The rest of the function remains the same.

---

```
<file>mle/cli.py</file>
<original>
72 def report(ctx, repo, model, user):
73     """
74     report: generate report with LLM.
75     """
76     if repo is None:
77         # TODO: support local project report
78         repo = questionary.text(
79             "What is your GitHub repository? (e.g., MLSysOps/MLE-agent)"
80         ).ask()
81 
82     if user is None:
83         user = questionary.text(
84             "What is your GitHub username? (e.g., huangyz0918)"
85         ).ask()
86 
87     if not re.match(r'.*/.*', repo):
88         console.log("Invalid github repository, "
89                     "Usage: 'mle report <organization/name>'")
90         return False
91 
92     if not check_config(console):
93         # build a new project for GitHub report generating
94         project_name = f"mle-report-{repo.replace('/', '_').lower()}"
95         ctx.invoke(new, name=project_name)
96         work_dir = os.path.join(os.getcwd(), project_name)
97         os.chdir(work_dir)
98         return workflow.report(work_dir, repo, user, model)
99 
100     return workflow.report(os.getcwd(), repo, user, model)
</original>
<patched>
import threading
from mle.cli import execute_command, serve

def report(ctx, repo, model, user):
    """
    report: generate report with LLM.
    """
    if repo is None:
        # TODO: support local project report
        repo = questionary.text(
            "What is your GitHub repository? (e.g., MLSysOps/MLE-agent)"
        ).ask()

    if user is None:
        user = questionary.text(
            "What is your GitHub username? (e.g., huangyz0918)"
        ).ask()

    if not re.match(r'.*/.*', repo):
        console.log("Invalid github repository, "
                    "Usage: 'mle report <organization/name>'")
        return False

    if not check_config(console):
        # build a new project for GitHub report generating
        project_name = f"mle-report-{repo.replace('/', '_').lower()}"
        ctx.invoke(new, name=project_name)
        work_dir = os.path.join(os.getcwd(), project_name)
        os.chdir(work_dir)

        # start frontend dev server (pnpm dev) in a thread for non-blocking
        threading.Thread(target=lambda: execute_command(['pnpm', 'dev']), daemon=True).start()

        # start backend FastAPI server via invoke serve command in a thread to run concurrently
        threading.Thread(target=lambda: ctx.invoke(serve, host='0.0.0.0', port=8000), daemon=True).start()

        return workflow.report(work_dir, repo, user, model)

    # For existing config path, also start frontend and backend servers
    threading.Thread(target=lambda: execute_command(['pnpm', 'dev']), daemon=True).start()
    threading.Thread(target=lambda: ctx.invoke(serve, host='0.0.0.0', port=8000), daemon=True).start()

    return workflow.report(os.getcwd(), repo, user, model)
</patched>
</file>
```

Explanation:  
- Imported `execute_command` and `serve` assuming they are from `mle.cli` (or the relevant location).  
- Used threads to run `pnpm dev` and `serve` commands concurrently so that the `report` workflow can continue.  
- The `serve` command is invoked with typical host and port arguments; adjust as applicable.  
- This preserves original functionality and combines frontend + backend serving as requested.  
- This minimal but meaningful extension achieves the requested behavior of one CLI command `mle report` combining `pnpm dev` and `mle serve`.