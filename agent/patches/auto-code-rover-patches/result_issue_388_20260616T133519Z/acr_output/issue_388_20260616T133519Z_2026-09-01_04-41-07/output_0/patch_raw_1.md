The current code accepts a `delete_existing` argument that, if set to True, deletes the memory and workspace folders at the start of the main run. The request is to remove this argument entirely and change the behavior such that if those folders exist, they are moved to a timestamped subfolder inside an "archive" directory. This keeps the project directory clean and only having current run data outside "archive". This also helps keep the `main.py` cleaner and makes it easier to handle separate logs for multiple runs in the future.

To do this, I will:
- Remove the `delete_existing` argument and associated code that deletes those folders.
- Add code before initializing the DBs to:
  - Check if the memory and workspace folders (with run_prefix) exist.
  - If they do, create an "archive" folder at the project root (if it doesn't exist).
  - Create a timestamped folder inside "archive" (format: YYYYMMDD_HHMMSS).
  - Move the old memory and workspace folders into that timestamped archive subfolder before proceeding.

This achieves the intended behavior. All other code remains as-is to keep existing functionality intact.


```
<file>gpt_engineer/main.py</file>
<original>19 def main(
20     project_path: str = typer.Argument("example", help="path"),
21     delete_existing: bool = typer.Argument(False, help="delete existing files"),
22     model: str = typer.Argument("gpt-4", help="model id string"),
23     temperature: float = 0.1,
24     steps_config: steps.Config = typer.Option(
25         steps.Config.DEFAULT, "--steps", "-s", help="decide which steps to run"
26     ),
27     verbose: bool = typer.Option(False, "--verbose", "-v"),
28     run_prefix: str = typer.Option(
29         "",
30         help=(
31             "run prefix, if you want to run multiple variants of the same project and "
32             "later compare them"
33         ),
34     ),
35 ):
36     logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
37 
38     input_path = Path(project_path).absolute()
39     memory_path = input_path / f"{run_prefix}memory"
40     workspace_path = input_path / f"{run_prefix}workspace"
41 
42     if delete_existing:
43         # Delete files and subdirectories in paths
44         shutil.rmtree(memory_path, ignore_errors=True)
45         shutil.rmtree(workspace_path, ignore_errors=True)
46 
47     model = fallback_model(model)
48 
49     ai = AI(
50         model=model,
51         temperature=temperature,
52     )
53 
54     dbs = DBs(
55         memory=DB(memory_path),
56         logs=DB(memory_path / "logs"),
57         input=DB(input_path),
58         workspace=DB(workspace_path),
59         preprompts=DB(Path(__file__).parent / "preprompts"),
60     )
61 
62     steps = STEPS[steps_config]
63     for step in steps:
64         messages = step(ai, dbs)
65         dbs.logs[step.__name__] = json.dumps(messages)
66 
67     collect_learnings(model, temperature, steps, dbs)
</original>
<patched>19 def main(
20     project_path: str = typer.Argument("example", help="path"),
21     model: str = typer.Argument("gpt-4", help="model id string"),
22     temperature: float = 0.1,
23     steps_config: steps.Config = typer.Option(
24         steps.Config.DEFAULT, "--steps", "-s", help="decide which steps to run"
25     ),
26     verbose: bool = typer.Option(False, "--verbose", "-v"),
27     run_prefix: str = typer.Option(
28         "",
29         help=(
30             "run prefix, if you want to run multiple variants of the same project and "
31             "later compare them"
32         ),
33     ),
34 ):
35     logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
36 
37     input_path = Path(project_path).absolute()
38     memory_path = input_path / f"{run_prefix}memory"
39     workspace_path = input_path / f"{run_prefix}workspace"
40 
41     # Archive existing memory and workspace folders if they exist
42     if memory_path.exists() or workspace_path.exists():
43         archive_path = input_path / "archive"
44         archive_path.mkdir(exist_ok=True)
45         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
46         archive_run_path = archive_path / timestamp
47         archive_run_path.mkdir()
48 
49         if memory_path.exists():
50             shutil.move(str(memory_path), str(archive_run_path / memory_path.name))
51         if workspace_path.exists():
52             shutil.move(str(workspace_path), str(archive_run_path / workspace_path.name))
53 
54     model = fallback_model(model)
55 
56     ai = AI(
57         model=model,
58         temperature=temperature,
59     )
60 
61     dbs = DBs(
62         memory=DB(memory_path),
63         logs=DB(memory_path / "logs"),
64         input=DB(input_path),
65         workspace=DB(workspace_path),
66         preprompts=DB(Path(__file__).parent / "preprompts"),
67     )
68 
69     steps = STEPS[steps_config]
70     for step in steps:
71         messages = step(ai, dbs)
72         dbs.logs[step.__name__] = json.dumps(messages)
73 
74     collect_learnings(model, temperature, steps, dbs)
</patched>
```

Additionally, since we use datetime and shutil for the new code, we need to ensure these are imported if not already:

```
<file>gpt_engineer/main.py</file>
<original>import logging
import json
import shutil
from pathlib import Path

import typer
</original>
<patched>import logging
import json
import shutil
from pathlib import Path
from datetime import datetime

import typer
</patched>
```