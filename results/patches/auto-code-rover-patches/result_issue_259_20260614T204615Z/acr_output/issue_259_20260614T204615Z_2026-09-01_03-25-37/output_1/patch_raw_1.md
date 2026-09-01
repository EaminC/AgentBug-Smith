Reasoning:
The issue requires enhancing the baseline workflow to establish a working directory and implement code scanning and embedding generation for RAG using the Memory class with OpenAI embeddings. The relevant file for workflow is `mle/workflow/baseline.py`.

Plan:
- Import necessary libraries: Memory from `mle.utils.memory`, OpenAIEmbeddings if needed, os, glob for file scanning.
- Establish work_dir as the baseline working directory if not exists.
- After step 5 (code generation), add a step to scan code files in work_dir (e.g., .py files), read content, generate embeddings using the embedding model (OpenAI embedding by default), and store them in the Memory instance for that work_dir.
- Ensure minimal interference with existing code and cache steps.
- No need to modify cli.py since it already calls baseline with os.getcwd() and model.
- memory.py seems fine for usage without modification.

This patch will add the embedding and RAG setup code in `baseline` function of `mle/workflow/baseline.py`.

---

# modification 1
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
32     import glob
33     from mle.utils.memory import Memory
34 
35     console = Console()
36     cache = WorkflowCache(work_dir, 'baseline')
37     model = load_model(work_dir, model)
38 
39     if not cache.is_empty():
40         step = ask_text(f"MLE has finished the following steps: \n{cache}\n"
41                         f"You can pick a step from 1 to {cache.current_step()} to resume\n"
42                         "(or ENTER to continue the workflow)")
43         if step:
44             step = int(step)
45             for i in range(step, cache.current_step() + 1):
46                 cache.remove(i)  # remove the stale step caches
47 
48     # ask for the data information
49     with cache(step=1, name="ask for the data information") as ca:
50         dataset = ca.resume("dataset")
51         if dataset is None:
52             advisor = AdviseAgent(model, console)
53             dataset = ask_text("Please provide your dataset information (a public dataset name or a local file path)")
54             if not dataset:
55                 print_in_box("The dataset is empty. Aborted", console, title="Error", color="red")
56                 return
57             dataset = advisor.clarify_dataset(dataset)
58             ca.store("dataset", dataset)
59 
60     # ask for the user requirement
61     with cache(step=2, name="ask for the user requirement") as ca:
62         ml_requirement = ca.resume("ml_requirement")
63         if ml_requirement is None:
64             ml_requirement = ask_text("Please provide your requirement")
65             if not ml_requirement:
66                 print_in_box("The user's requirement is empty. Aborted", console, title="Error", color="red")
67                 return
68         ca.store("ml_requirement", ml_requirement)
69 
70     # advisor agent gives suggestions in a report
71     with cache(step=3, name="MLE advisor agent provides a high-level report") as ca:
72         advisor_report = ca.resume("advisor_report")
73         if advisor_report is None:
74             advisor = AdviseAgent(model, console)
75             advisor_report = advisor.interact("[green]User Requirement:[/green] " + ml_requirement + "\n" + ask_data(dataset))
76         ca.store("advisor_report", advisor_report)
77 
78     # plan agent generates the coding plan
79     with cache(step=4, name="MLE plan agent generates a dev plan") as ca:
80         coding_plan = ca.resume("coding_plan")
81         if coding_plan is None:
82             planner = PlanAgent(model, console)
83             coding_plan = planner.interact(advisor_report)
84         ca.store("coding_plan", coding_plan)
85 
86     # code agent codes the tasks and debug with the debug agent
87     with cache(step=5, name="MLE code&debug agents start to work") as ca:
88         coder = CodeAgent(model, work_dir, console)
89         coder.read_requirement(advisor_report)
90         debugger = DebugAgent(model, console)
91 
92         is_auto_mode = questionary.confirm(
93             "MLE developer is about to start to code.\n"
94             "Choose to debug or not (If no, MLE agent will only focus on coding tasks,"
95             " and you have to run and debug the code yourself)?"
96         ).ask()
97 
98         for current_task in coding_plan.get('tasks'):
99             code_report = coder.interact(current_task)
100             is_debugging = code_report.get('debug')
101 
102             if is_auto_mode:
103                 while True:
104                     if is_debugging == 'true' or is_debugging == 'True':
105                         with console.status("MLE Debug Agent is executing and debugging the code..."):
106                             debug_report = debugger.analyze(code_report)
107                         if debug_report.get('status') == 'success':
108                             break
109                         else:
110                             code_report = coder.debug(current_task, debug_report)
111                     else:
112                         break
113 
114     # Step 6: Scan code files in work_dir and generate embeddings for RAG
115     with cache(step=6, name="Generate embeddings for RAG") as ca:
116         mem = Memory(work_dir)
117         # Only process if not already done
118         existing_count = mem.count()
119         if existing_count == 0:
120             # Find code files (e.g., .py files) in work_dir recursively
121             pattern = os.path.join(work_dir, '**', '*.py')
122             files = glob.glob(pattern, recursive=True)
123             # Read contents and prepare for embedding
124             documents = []
125             for file in files:
126                 try:
127                     with open(file, 'r', encoding='utf-8') as f:
128                         content = f.read()
129                         documents.append({
130                             'query': content,
131                             'response': f"File: {os.path.relpath(file, work_dir)}"
132                         })
133                 except Exception as e:
134                     console.print(f"[red]Failed to read file {file} for embedding: {e}[/red]")
135 
136             if documents:
137                 mem.add_query(documents)
138                 console.print(f"[green]Added {len(documents)} code snippets to Memory embeddings for RAG.[/green]")
139             else:
140                 console.print("[yellow]No source code files found to embed for RAG.[/yellow]")
141         else:
142             console.print(f"[blue]Memory embeddings already exist with {existing_count} records, skipping embedding generation.[/blue]")
</patched>
```