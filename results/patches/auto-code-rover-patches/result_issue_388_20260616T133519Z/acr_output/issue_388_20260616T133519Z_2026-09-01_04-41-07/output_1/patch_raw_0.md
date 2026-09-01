The main change involves removing the `delete_existing` argument and related logic from the `main` function and instead adding a procedure at the start of the function that checks if the `memory` and `workspace` folders exist. If they do, they are moved into a timestamped subfolder inside an `archive` directory within the project directory. This way, the previous run's files are archived and a fresh run starts with clean folders. This matches the requirement to keep main.py cleaner and have all files except `archive` be from the most recent run.

To do this, I'll:
- Import `datetime` and `shutil` if not already imported.
- Remove the `delete_existing` argument from `main`.
- Add logic at the top of `main` that:
  - Checks if `memory_path` and/or `workspace_path` exist.
  - Creates the `archive` directory if not exists.
  - Creates a timestamped subfolder like `YYYYmmdd_HHMMSS`.
  - Moves existing `memory` and `workspace` folders into that archive folder.
- The existing flow creating AI and DB instances, running steps, etc., remains unchanged.

This preserves existing functionality and fulfills the new archiving behavior.

---

# modification 1
```
<file>gpt_engineer/main.py</file>
<original>def main(
    project_path: str = typer.Argument("example", help="path"),
    delete_existing: bool = typer.Argument(False, help="delete existing files"),
    model: str = typer.Argument("gpt-4", help="model id string"),
    temperature: float = 0.1,
    steps_config: steps.Config = typer.Option(
        steps.Config.DEFAULT, "--steps", "-s", help="decide which steps to run"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    run_prefix: str = typer.Option(
        "",
        help=(
            "run prefix, if you want to run multiple variants of the same project and "
            "later compare them"
        ),
    ),
):</original>
<patched>import datetime
import shutil

def main(
    project_path: str = typer.Argument("example", help="path"),
    model: str = typer.Argument("gpt-4", help="model id string"),
    temperature: float = 0.1,
    steps_config: steps.Config = typer.Option(
        steps.Config.DEFAULT, "--steps", "-s", help="decide which steps to run"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    run_prefix: str = typer.Option(
        "",
        help=(
            "run prefix, if you want to run multiple variants of the same project and "
            "later compare them"
        ),
    ),
):</patched>
```

# modification 2
```
<file>gpt_engineer/main.py</file>
<original>    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    input_path = Path(project_path).absolute()
    memory_path = input_path / f"{run_prefix}memory"
    workspace_path = input_path / f"{run_prefix}workspace"

    if delete_existing:
        # Delete files and subdirectories in paths
        shutil.rmtree(memory_path, ignore_errors=True)
        shutil.rmtree(workspace_path, ignore_errors=True)

    model = fallback_model(model)

    ai = AI(
        model=model,
        temperature=temperature,
    )

    dbs = DBs(
        memory=DB(memory_path),
        logs=DB(memory_path / "logs"),
        input=DB(input_path),
        workspace=DB(workspace_path),
        preprompts=DB(Path(__file__).parent / "preprompts"),
    )

    steps = STEPS[steps_config]
    for step in steps:
        messages = step(ai, dbs)
        dbs.logs[step.__name__] = json.dumps(messages)

    collect_learnings(model, temperature, steps, dbs)</original>
<patched>    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    input_path = Path(project_path).absolute()
    memory_path = input_path / f"{run_prefix}memory"
    workspace_path = input_path / f"{run_prefix}workspace"

    # Archive existing memory and workspace folders if they exist
    archive_path = input_path / "archive"
    if memory_path.exists() or workspace_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_archive = archive_path / timestamp
        dest_archive.mkdir(parents=True, exist_ok=True)

        if memory_path.exists():
            shutil.move(str(memory_path), str(dest_archive / memory_path.name))
        if workspace_path.exists():
            shutil.move(str(workspace_path), str(dest_archive / workspace_path.name))

    # Recreate empty memory and workspace folders for new run
    memory_path.mkdir(parents=True, exist_ok=True)
    workspace_path.mkdir(parents=True, exist_ok=True)

    model = fallback_model(model)

    ai = AI(
        model=model,
        temperature=temperature,
    )

    dbs = DBs(
        memory=DB(memory_path),
        logs=DB(memory_path / "logs"),
        input=DB(input_path),
        workspace=DB(workspace_path),
        preprompts=DB(Path(__file__).parent / "preprompts"),
    )

    steps = STEPS[steps_config]
    for step in steps:
        messages = step(ai, dbs)
        dbs.logs[step.__name__] = json.dumps(messages)

    collect_learnings(model, temperature, steps, dbs)</patched>
```