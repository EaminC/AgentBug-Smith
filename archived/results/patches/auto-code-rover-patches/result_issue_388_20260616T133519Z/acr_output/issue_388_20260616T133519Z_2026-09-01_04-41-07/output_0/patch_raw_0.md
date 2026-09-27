The issue requests removing the "run_id" and "delete_existing" options (delete_existing is present in the signature and usage), and instead adding logic that when a memory or workspace folder (considering the run_prefix) already exists, it should be moved into an archive folder with a timestamp name under an "archive" directory. This makes the main directory clean and only contains files from the most recent run.

Therefore, in main.py:

- Remove the delete_existing argument from main() signature.
- Remove the conditional block that deletes memory_path and workspace_path folders.
- Add logic at the start to check if memory_path and workspace_path exist.
- If they do, create an "archive" directory at the project root if needed.
- Create a new timestamped folder under "archive", for example with datetime.now().strftime.
- Move the existing memory_path and workspace_path folders inside that archive folder.
- Leave the rest of the logic unchanged.

This way, the old memory and workspace get moved aside instead of simply deleted, and the main.py is cleaner and ready for future enhancements.

---

# modification 1
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
<patched>19 from datetime import datetime
20 
21 def main(
22     project_path: str = typer.Argument("example", help="path"),
23     model: str = typer.Argument("gpt-4", help="model id string"),
24     temperature: float = 0.1,
25     steps_config: steps.Config = typer.Option(
26         steps.Config.DEFAULT, "--steps", "-s", help="decide which steps to run"
27     ),
28     verbose: bool = typer.Option(False, "--verbose", "-v"),
29     run_prefix: str = typer.Option(
30         "",
31         help=(
32             "run prefix, if you want to run multiple variants of the same project and "
33             "later compare them"
34         ),
35     ),
36 ):
37     logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
38 
39     input_path = Path(project_path).absolute()
40     memory_path = input_path / f"{run_prefix}memory"
41     workspace_path = input_path / f"{run_prefix}workspace"
42 
43     archive_path = input_path / "archive"
44     if memory_path.exists() or workspace_path.exists():
45         archive_path.mkdir(exist_ok=True)
46         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
47         archive_folder = archive_path / timestamp
48         archive_folder.mkdir()
49         if memory_path.exists():
50             shutil.move(str(memory_path), str(archive_folder / f"{run_prefix}memory"))
51         if workspace_path.exists():
52             shutil.move(str(workspace_path), str(archive_folder / f"{run_prefix}workspace"))
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
Summary:
- Removed the delete_existing argument and all its usage.
- Added a new block to check if memory or workspace folders exist, and move them into a timestamped archive under archive/.
- Imported datetime at the top to get current timestamp.  
- Kept remaining logic untouched.