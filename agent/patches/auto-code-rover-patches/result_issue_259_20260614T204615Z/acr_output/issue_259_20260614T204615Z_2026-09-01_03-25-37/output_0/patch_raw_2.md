Reasoning:
The main request is to add local code scanning and embedding generation in the baseline workflow, which is the `baseline` function in `mle/workflow/baseline.py`. For this, we should establish a workdir for the baseline mode, scan the code files present under that workdir, generate embeddings using the Memory class (which is backed by LanceDB), and save the code snippets and their embeddings there. This will provide the RAG capabilities downstream.

Steps:
1. Import the newly added Memory class from `mle.utils.memory` in `baseline.py`.
2. After loading the model and user inputs, add a step to scan local code files from the work_dir, read their content, and add to the Memory instance for embedding generation.
3. Use the recommended OpenAI embedding model name and model key from configuration.
4. This scanning and adding embeddings step should happen early in the workflow so that the later steps can query embeddings if needed.
5. Preserve all existing functionalities without breaking anything.
6. Create a workspace folder `.mle` inside work_dir consistent with Memory's persistent path.
7. The scanning should consider common code file suffixes to read (like `.py`, `.txt`, `.md`, `.json`, `.yaml`, etc.) for generality.
8. Use console print or similar to indicate progress.

No changes to `memory.py` are required because the provided implementation already correctly supports embeddings with OpenAI or default ChromaDB embeddings and basic CRUD.

Patch:

```
<file>mle/workflow/baseline.py</file>
<original>25 def baseline(work_dir: str, model=None):
26     """
27     The workflow of the baseline mode.
28     :return:
29     """
30 
31     console = Console()
32     cache = WorkflowCache(work_dir, 'baseline')
33     model = load_model(work_dir, model)
34 
35     if not cache.is_empty():
36         step = ask_text(f"MLE has finished the following steps: \n{cache}\n"
37                         f"You can pick a step from 1 to {cache.current_step()} to resume\n"
38                         "(or ENTER to continue the workflow)")
39         if step:
40             step = int(step)
41             for i in range(step, cache.current_step() + 1):
42                 cache.remove(i)  # remove the stale step caches
43 
44     # ask for the data information
45     with cache(step=1, name="ask for the data information") as ca:
46         dataset = ca.resume("dataset")
47         if dataset is None:
48             advisor = AdviseAgent(model, console)
49             dataset = ask_text("Please provide your dataset information (a public dataset name or a local file path)")
50             if not dataset:
51                 print_in_box("The dataset is empty. Aborted", console, title="Error", color="red")
52                 return
53             dataset = advisor.clarify_dataset(dataset)
54             ca.store("dataset", dataset)
55 
56     # ask for the user requirement
57     with cache(step=2, name="ask for the user requirement") as ca:
58         ml_requirement = ca.resume("ml_requirement")
59         if ml_requirement is None:
60             ml_requirement = ask_text("Please provide your requirement")
61             if not ml_requirement:
62                 print_in_box("The user's requirement is empty. Aborted", console, title="Error", color="red")
63                 return
64         ca.store("ml_requirement", ml_requirement)
65 
66     # advisor agent gives suggestions in a report
67     with cache(step=3, name="MLE advisor agent provides a high-level report") as ca:
68         advisor_report = ca.resume("advisor_report")
69         if advisor_report is None:
70             advisor = AdviseAgent(model, console)
71             advisor_report = advisor.interact("[green]User Requirement:[/green] " + ml_requirement + "\n" + ask_data(dataset))
72         ca.store("advisor_report", advisor_report)
73 
74     # plan agent generates the coding plan
75     with cache(step=4, name="MLE plan agent generates a dev plan") as ca:
76         coding_plan = ca.resume("coding_plan")
77         if coding_plan is None:
78             planner = PlanAgent(model, console)
79             coding_plan = planner.interact(advisor_report)
80         ca.store("coding_plan", coding_plan)
81 
82     # code agent codes the tasks and debug with the debug agent
83     with cache(step=5, name="MLE code&debug agents start to work") as ca:
84         coder = CodeAgent(model, work_dir, console)
85         coder.read_requirement(advisor_report)
86         debugger = DebugAgent(model, console)
87 
88         is_auto_mode = questionary.confirm(
89             "MLE developer is about to start to code.\n"
90             "Choose to debug or not (If no, MLE agent will only focus on coding tasks,"
91             " and you have to run and debug the code yourself)?"
92         ).ask()
93 
94         for current_task in coding_plan.get('tasks'):
95             code_report = coder.interact(current_task)
96             is_debugging = code_report.get('debug')
97 
98             if is_auto_mode:
99                 while True:
100                     if is_debugging == 'true' or is_debugging == 'True':
101                         with console.status("MLE Debug Agent is executing and debugging the code..."):
102                             debug_report = debugger.analyze(code_report)
103                         if debug_report.get('status') == 'success':
104                             break
105                         else:
106                             code_report = coder.debug(current_task, debug_report)
107                     else:
108                         break
</original>
<patched>25 def baseline(work_dir: str, model=None):
26     """
27     The workflow of the baseline mode.
28     :return:
29     """
30 
31     import os
32     from pathlib import Path
33     from mle.utils.memory import Memory
34 
35     console = Console()
36     cache = WorkflowCache(work_dir, 'baseline')
37     model = load_model(work_dir, model)
38 
39     # Step 0: Scan local code files and index embeddings for RAG
40     with console.status("[bold green]Scanning local code base and generating embeddings for RAG..."):
41         memory = Memory(work_dir, embedding_model="text-embedding-ada-002")
42         code_extensions = ['.py', '.txt', '.md', '.json', '.yaml', '.yml', '.toml', '.csv', '.ini']
43         code_snippets = []
44         snippet_ids = []
45 
46         base_path = Path(work_dir)
47         for root, dirs, files in os.walk(base_path):
48             # Ignore hidden directories like .mle
49             dirs[:] = [d for d in dirs if not d.startswith('.')]
50             for file in files:
51                 if any(file.endswith(ext) for ext in code_extensions):
52                     file_path = Path(root) / file
53                     try:
54                         with open(file_path, "r", encoding="utf-8") as f:
55                             content = f.read()
56                             if content.strip():
57                                 # Use file path + maybe snippet offset for id if needed
58                                 snippet_id = str(file_path.relative_to(base_path))
59                                 code_snippets.append({"query": content, "response": f"source: {snippet_id}"})
60                                 snippet_ids.append(snippet_id)
61                     except Exception as e:
62                         console.print(f"[yellow]Warning: Failed to read file {file_path}: {e}")
63 
64         if code_snippets:
65             memory.add_query(code_snippets, collection="codebase", idx=snippet_ids)
66         else:
67             console.print("[yellow]No local code snippets found for embedding.")
68 
69     if not cache.is_empty():
70         step = ask_text(f"MLE has finished the following steps: \n{cache}\n"
71                         f"You can pick a step from 1 to {cache.current_step()} to resume\n"
72                         "(or ENTER to continue the workflow)")
73         if step:
74             step = int(step)
75             for i in range(step, cache.current_step() + 1):
76                 cache.remove(i)  # remove the stale step caches
77 
78     # ask for the data information
79     with cache(step=1, name="ask for the data information") as ca:
80         dataset = ca.resume("dataset")
81         if dataset is None:
82             advisor = AdviseAgent(model, console)
83             dataset = ask_text("Please provide your dataset information (a public dataset name or a local file path)")
84             if not dataset:
85                 print_in_box("The dataset is empty. Aborted", console, title="Error", color="red")
86                 return
87             dataset = advisor.clarify_dataset(dataset)
88             ca.store("dataset", dataset)
89 
90     # ask for the user requirement
91     with cache(step=2, name="ask for the user requirement") as ca:
92         ml_requirement = ca.resume("ml_requirement")
93         if ml_requirement is None:
94             ml_requirement = ask_text("Please provide your requirement")
95             if not ml_requirement:
96                 print_in_box("The user's requirement is empty. Aborted", console, title="Error", color="red")
97                 return
98         ca.store("ml_requirement", ml_requirement)
99 
100     # advisor agent gives suggestions in a report
101     with cache(step=3, name="MLE advisor agent provides a high-level report") as ca:
102         advisor_report = ca.resume("advisor_report")
103         if advisor_report is None:
104             advisor = AdviseAgent(model, console)
105             advisor_report = advisor.interact("[green]User Requirement:[/green] " + ml_requirement + "\n" + ask_data(dataset))
106         ca.store("advisor_report", advisor_report)
107 
108     # plan agent generates the coding plan
109     with cache(step=4, name="MLE plan agent generates a dev plan") as ca:
110         coding_plan = ca.resume("coding_plan")
111         if coding_plan is None:
112             planner = PlanAgent(model, console)
113             coding_plan = planner.interact(advisor_report)
114         ca.store("coding_plan", coding_plan)
115 
116     # code agent codes the tasks and debug with the debug agent
117     with cache(step=5, name="MLE code&debug agents start to work") as ca:
118         coder = CodeAgent(model, work_dir, console)
119         coder.read_requirement(advisor_report)
120         debugger = DebugAgent(model, console)
121 
122         is_auto_mode = questionary.confirm(
123             "MLE developer is about to start to code.\n"
124             "Choose to debug or not (If no, MLE agent will only focus on coding tasks,"
125             " and you have to run and debug the code yourself)?"
126         ).ask()
127 
128         for current_task in coding_plan.get('tasks'):
129             code_report = coder.interact(current_task)
130             is_debugging = code_report.get('debug')
131 
132             if is_auto_mode:
133                 while True:
134                     if is_debugging == 'true' or is_debugging == 'True':
135                         with console.status("MLE Debug Agent is executing and debugging the code..."):
136                             debug_report = debugger.analyze(code_report)
137                         if debug_report.get('status') == 'success':
138                             break
139                         else:
140                             code_report = coder.debug(current_task, debug_report)
141                     else:
142                         break
</patched>
```