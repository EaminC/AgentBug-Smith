The issue requests adding an explicit code review step with an LLM performing QA-like testing and optionally generating fixes ("self-healing"). This requires:

1. Extending the `Review` class in `learning.py` with methods to:
    - Request QA test cases from the LLM based on the project specification.
    - Check whether generated code passes those QA test cases by inspecting code.
    - Generate code blocks with fixes if issues are found, allowing automatic corrections.
2. Adding helper functions or prompts in `steps.py` to implement these interactions with the LLM, specifically:
    - A prompt for generating QA tasks.
    - A prompt for reviewing generated code against QA tasks.
    - A prompt to produce fixing code.
3. Adding a function that orchestrates these review steps, calling the helper functions and applying fixes if any.
4. Optionally, integrating this new review step into the workflow steps dictionary if needed.

The patch focuses on minimal changes:
- Add new methods to the `Review` dataclass.
- Add the necessary prompting and step function in `steps.py`.
- Keep existing code intact.

---

# modification 1
```
<file>gpt_engineer/cli/learning.py</file>
<original>61 class Review:
62     ran: Optional[bool]
63     perfect: Optional[bool]
64     works: Optional[bool]
65     comments: str
66     raw: str
</original>
<patched>61 from typing import List, Optional
62 from pydantic import BaseModel
63 
64 class Review(BaseModel):
65     ran: Optional[bool] = None
66     perfect: Optional[bool] = None
67     works: Optional[bool] = None
68     comments: Optional[str] = None
69     raw: Optional[str] = None
70 
71     def get_qa_tasks_prompt(self, project_spec: str) -> str:
72         """Generate a prompt to ask the LLM what QA tasks a QA person would run."""
73         prompt = (
74             "Given the following project specification, list the QA tasks a QA person would manually test, "
75             "as short, precise checks (e.g., 'does snake move', 'does the snake change direction when a key is pressed'):\n\n"
76             f"{project_spec}\n\n"
77             "Provide the list as bullet points."
78         )
79         return prompt
80 
81     def get_code_review_prompt(self, generated_code: str, qa_tasks: List[str]) -> str:
82         """Generate a prompt asking the LLM to analyze the code for each QA task and state if it passes or is broken."""
83         tasks_formatted = "\n".join(f"- {task}" for task in qa_tasks)
84         prompt = (
85             "Based on the given code below, analyze whether the code is expected to pass the following QA tasks "
86             "just by inspecting the code. For each task, respond with PASS or FAIL and a brief explanation.\n\n"
87             f"QA Tasks:\n{tasks_formatted}\n\n"
88             f"Code:\n```python\n{generated_code}\n```\n"
89             "Please output a list with each task, its PASS/FAIL status, and comments."
90         )
91         return prompt
92 
93     def get_self_healing_fix_prompt(self, generated_code: str, failed_tasks_details: str) -> str:
94         """Generate a prompt for the LLM to produce fixing code blocks to overwrite files to fix the identified issues."""
95         prompt = (
96             "The following code has failed some QA tasks based on the analysis.\n"
97             "Below are the failed QA tasks and their issues:\n"
98             f"{failed_tasks_details}\n\n"
99             "Please provide corrected code blocks to fix these issues. The code blocks should include file paths "
100             "if possible (e.g., ```file.py\ncode\n```). "
101             "Output only the fixed code blocks that overwrite the files."
102         )
103         # Include the code in the prompt to allow guided fixing
104         # Maybe include the original code as context (not shown here for brevity).
105         return prompt
</patched>
```

# modification 2
```
<file>gpt_engineer/core/steps.py</file>
<original>...
65 from gpt_engineer.cli.file_selector import FILE_LIST_NAME, ask_for_files
66 from gpt_engineer.cli.learning import human_review_input
67 
68 # Type hint for chat messages
69 Message = Union[AIMessage, HumanMessage, SystemMessage]
70 
71 
72 def setup_sys_prompt(dbs: DBs) -> str:
...
</original>
<patched>...
65 from gpt_engineer.cli.file_selector import FILE_LIST_NAME, ask_for_files
66 from gpt_engineer.cli.learning import human_review_input, Review
67 
68 # Type hint for chat messages
69 Message = Union[AIMessage, HumanMessage, SystemMessage]
70 
71 def generate_qa_tasks(ai: AI, dbs: DBs) -> List[Message]:
72     """
73     Ask the LLM what QA tasks a QA person would manually test based on the project specification.
74     """
75     review = Review()
76     project_spec = dbs.input.get("prompt", "")
77     prompt = review.get_qa_tasks_prompt(project_spec)
78 
79     messages = ai.start(
80         system="You are an expert QA engineer.",
81         user=prompt,
82         step_name=generate_qa_tasks.__name__,
83     )
84     return messages
85 
86 def analyze_code_for_qa(ai: AI, dbs: DBs, qa_tasks: List[str]) -> List[Message]:
87     """
88     Ask the LLM if the generated code is expected to pass each QA task just by inspecting the code.
89     """
90 
91     # Get generated code from memory (assuming combined all code files concatenated)
92     generated_code = dbs.memory.get("all_output.txt", "")
93     review = Review()
94     prompt = review.get_code_review_prompt(generated_code, qa_tasks)
95 
96     messages = ai.start(
97         system="You are an expert QA engineer analyzing code against QA tasks.",
98         user=prompt,
99         step_name=analyze_code_for_qa.__name__,
100     )
101     return messages
102 
103 def self_healing_fix(ai: AI, dbs: DBs, failed_tasks_details: str) -> List[Message]:
104     """
105     Ask the LLM to output _code blocks_ to overwrite files fixing issues from failed QA tasks.
106     """
107     generated_code = dbs.memory.get("all_output.txt", "")
108     review = Review()
109     prompt = review.get_self_healing_fix_prompt(generated_code, failed_tasks_details)
110 
111     messages = ai.start(
112         system="You are an expert software engineer fixing code based on QA failures.",
113         user=prompt,
114         step_name=self_healing_fix.__name__,
115     )
116     # Overwrite files with the fixes
117     from gpt_engineer.core.chat_to_files import overwrite_files_with_edits
118     overwrite_files_with_edits(messages[-1].content.strip(), dbs)
119 
120     return messages
121 
122 def code_review_and_self_healing(ai: AI, dbs: DBs) -> List[Message]:
123     """
124     A combined step implementing the explicit code review and optional self healing:
125       1. Get QA tasks from LLM.
126       2. Analyze the generated code for each QA task.
127       3. If there are failures, ask the LLM to produce code fixes.
128     """
129 
130     # Step 1: Get QA tasks
131     qa_tasks_msg = generate_qa_tasks(ai, dbs)
132     # Parse QA tasks from response
133     qa_tasks_text = qa_tasks_msg[-1].content.strip()
134     qa_tasks = []
135     for line in qa_tasks_text.splitlines():
136         line = line.strip()
137         if line.startswith("- ") or line.startswith("* "):
138             qa_tasks.append(line[2:].strip())
139         elif line:
140             qa_tasks.append(line)
141 
142     if not qa_tasks:
143         print("No QA tasks were generated; skipping code review.")
144         return []
145 
146     # Step 2: Analyze code for QA tasks
147     analysis_msg = analyze_code_for_qa(ai, dbs, qa_tasks)
148     analysis_text = analysis_msg[-1].content.strip()
149 
150     # Check if any task failed by simple heuristic looking for "FAIL" keyword
151     failed_lines = []
152     for line in analysis_text.splitlines():
153         if "FAIL" in line.upper():
154             failed_lines.append(line)
155 
156     if not failed_lines:
157         print("Code review indicates all QA tasks pass.")
158         # Store review info to memory as well
159         dbs.memory["code_review"] = analysis_text
160         return analysis_msg
161 
162     print("Code review detected issues in the following tasks:")
163     for line in failed_lines:
164         print(line)
165 
166     # Step 3: Generate fixing code blocks to fix the issues
167     fix_msg = self_healing_fix(ai, dbs, "\n".join(failed_lines))
168 
169     # Optional: we could rerun analysis or regenerate QA tasks, but skip for now.
170 
171     # Store both review analysis and fix output to memory
172     dbs.memory["code_review"] = analysis_text
173     dbs.memory["self_healing_fixes"] = fix_msg[-1].content.strip()
174 
175     return fix_msg
176 
177 </patched>
```

# modification 3
```
<file>gpt_engineer/core/steps.py</file>
<original>650 STEPS = {
651     Config.DEFAULT: [
652         simple_gen,
653         gen_entrypoint,
654         execute_entrypoint,
655         human_review,
656     ],
657     Config.LITE: [
658         lite_gen,
659     ],
660     Config.CLARIFY: [
661         clarify,
662         gen_clarified_code,
663         gen_entrypoint,
664         execute_entrypoint,
665         human_review,
666     ],
667     Config.BENCHMARK: [
668         simple_gen,
669         gen_entrypoint,
670     ],
671     Config.SIMPLE: [
672         simple_gen,
673         gen_entrypoint,
674         execute_entrypoint,
675     ],
676     Config.USE_FEEDBACK: [use_feedback, gen_entrypoint, execute_entrypoint, human_review],
677     Config.EXECUTE_ONLY: [execute_entrypoint],
678     Config.EVALUATE: [execute_entrypoint, human_review],
679     Config.IMPROVE_CODE: [
680         set_improve_filelist,
681         get_improve_prompt,
682         improve_existing_code,
683     ],
684     Config.EVAL_IMPROVE_CODE: [assert_files_ready, improve_existing_code],
685     Config.EVAL_NEW_CODE: [simple_gen],
686 }
687 """</original>
<patched>650 STEPS = {
651     Config.DEFAULT: [
652         simple_gen,
653         gen_entrypoint,
654         execute_entrypoint,
655         human_review,
656     ],
657     Config.LITE: [
658         lite_gen,
659     ],
660     Config.CLARIFY: [
661         clarify,
662         gen_clarified_code,
663         gen_entrypoint,
664         execute_entrypoint,
665         human_review,
666     ],
667     Config.BENCHMARK: [
668         simple_gen,
669         gen_entrypoint,
670     ],
671     Config.SIMPLE: [
672         simple_gen,
673         gen_entrypoint,
674         execute_entrypoint,
675     ],
676     Config.USE_FEEDBACK: [use_feedback, gen_entrypoint, execute_entrypoint, human_review],
677     Config.EXECUTE_ONLY: [execute_entrypoint],
678     Config.EVALUATE: [execute_entrypoint, human_review],
679     Config.IMPROVE_CODE: [
680         set_improve_filelist,
681         get_improve_prompt,
682         improve_existing_code,
683     ],
684     Config.EVAL_IMPROVE_CODE: [assert_files_ready, improve_existing_code],
685     Config.EVAL_NEW_CODE: [simple_gen],
686     # New explicit code review + self-healing step example (optional)
687     "code_review_self_healing": [
688         code_review_and_self_healing,
689         gen_entrypoint,
690         execute_entrypoint,
691         human_review,
692     ],
693 }
694 </patched>
```