The issue requests implementing an explicit "code review" step plus a self-healing mechanism driven by the LLM. The proposed workflow suggests:

1. After code generation, ask the LLM what a QA person would test, based on the project specification.
2. For each QA task, ask if the generated code is expected to pass the QA task or if something seems broken.
3. If broken, optionally generate code blocks that overwrite files to fix issues.

We have two key files relevant:

- `gpt_engineer/cli/learning.py`: where the `Review` class is defined but currently just holds metadata. We should extend `Review` with methods that implement these "review" and "self-healing" interactions with the LLM.

- `gpt_engineer/core/steps.py`: where prompts and workflow step functions are defined. We need to add prompt construction functions to interact with the LLM for review and fix generation. Also, add new workflow step functions that call these prompts and handle the review+fix logic.

Design:

- In `cli/learning.py`:

  - Add methods to Review class such as:
  
    - `ask_for_qa_tasks(ai: AI, dbs: DBs)` - asks the LLM to list QA tests for the code based on project spec.
    - `code_review(ai: AI, dbs: DBs, qa_tasks: List[str])` - for each QA task, ask if the code is expected to pass.
    - `self_heal(ai: AI, dbs: DBs, issues: List[str])` - for detected failing QA tasks, ask LLM to generate fix code blocks that overwrite files.
  
- In `core/steps.py`:

  - Add helper functions that generate the prompts for each of the above purposes.
  
  - Add one or more workflow functions that combine these calls, so the main workflow can insert the review/self-heal step explicitly.
  
- We will avoid changing existing workflows but build the pieces so a new workflow step can be inserted later.

- For all calls to LLM, reuse the AI interface consistent with other steps.

Now providing the patch with these modifications.

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
62
63 class Review:
64     ran: Optional[bool]
65     perfect: Optional[bool]
66     works: Optional[bool]
67     comments: str
68     raw: str
69
70     def ask_for_qa_tasks(self, ai, dbs) -> List[str]:
71         """
72         Ask the LLM to generate a list of QA tasks a QA person would perform based on the project spec.
73         Returns a list of textual QA tasks.
74         """
75         system_prompt = (
76             "You are a QA engineer. Given the project specification, list the QA tasks "
77             "that a manual QA person would perform to test the generated code. "
78             "Provide the list as bullet points, each bullet being a concise test description.\n\n"
79             "Project specification:\n"
80             + dbs.input["prompt"]
81         )
82         messages = ai.start(system_prompt, "", step_name="ask_for_qa_tasks")
83         content = messages[-1].content.strip()
84         # Extract list of QA tasks from content: split by lines that look like bullet points
85         tasks = []
86         for line in content.splitlines():
87             line = line.strip()
88             if line.startswith("-") or line.startswith("*"):
89                 line = line[1:].strip()
90             if line:
91                 tasks.append(line)
92         return tasks
93
94     def code_review(self, ai, dbs, qa_tasks: List[str]) -> List[str]:
95         """
96         For each QA task, ask the LLM if the generated code would pass it by inspection,
97         or if something seems broken. Returns list of failing QA tasks descriptions.
98         """
99         failing_tasks = []
100        # Load all generated code as one string from workspace files (or memory)
101        code_text = ""
102        # Aggregate all code files content from dbs.workspace
103        for filename, content in dbs.workspace.items():
104            if isinstance(content, str):
105                code_text += f"\nFilename: {filename}\n{content}\n"
106
107        for task in qa_tasks:
108            system_prompt = (
109                "You are a QA engineer reviewing generated code. "
110                "Given the QA test description and the generated code below, "
111                "answer with either 'PASS' or 'FAIL' and an explanation if it would pass or fail the test.\n\n"
112                f"QA test:\n{task}\n\nGenerated code:\n{code_text}"
113            )
114            messages = ai.start(system_prompt, "", step_name="code_review")
115            resp = messages[-1].content.strip().lower()
116            if "fail" in resp:
117                failing_tasks.append(task)
118        return failing_tasks
119
120    def self_heal(self, ai, dbs, failing_tasks: List[str]) -> bool:
121        """
122        For each failing QA task, ask the LLM to generate fixes as code blocks that
123        overwrite files to fix issues. Returns True if any fix was applied.
124        """
125        if not failing_tasks:
126            return False
127        fixes_applied = False
128        for task in failing_tasks:
129            system_prompt = (
130                "You are a software engineer tasked with fixing a failing QA test.\n"
131                "The QA test failed: " + task + "\n"
132                "Based on the previously generated code, provide improved code in code blocks that overwrite the necessary files to fix the issue.\n"
133                "Only provide the fixed code blocks, do not explain or add text.\n"
134            )
135            # Provide all current code as context
136            code_text = ""
137            for filename, content in dbs.workspace.items():
138                if isinstance(content, str):
139                    code_text += f"\nFilename: {filename}\n{content}\n"
140
141            messages = ai.start(system_prompt + "\nCode base:\n" + code_text, "", step_name="self_heal")
142            content = messages[-1].content.strip()
143            # Apply fixes by overwriting files with the code blocks extracted
144            from gpt_engineer.core.chat_to_files import overwrite_files_with_edits
145            overwrite_files_with_edits(content, dbs)
146            fixes_applied = True
147        return fixes_applied
</patched>
```

# modification 2
```
<file>gpt_engineer/core/steps.py</file>
<original>46 """
47 
48 import inspect
49 import re
50 import subprocess
51 
52 from enum import Enum
53 from typing import List, Union
54 
55 from langchain.schema import AIMessage, HumanMessage, SystemMessage
56 from termcolor import colored
57 
58 from gpt_engineer.core.ai import AI
59 from gpt_engineer.core.chat_to_files import (
60     format_file_to_input,
61     get_code_strings,
62     overwrite_files_with_edits,
63     to_files_and_memory,
64 )
65 from gpt_engineer.core.db import DBs
66 from gpt_engineer.cli.file_selector import FILE_LIST_NAME, ask_for_files
67 from gpt_engineer.cli.learning import human_review_input
68 
69 # Type hint for chat messages
70 Message = Union[AIMessage, HumanMessage, SystemMessage]
71 
72 
73 def setup_sys_prompt(dbs: DBs) -> str:
74     """
75     Constructs a system prompt for the AI based on predefined instructions and philosophies.
76 
77     This function is responsible for setting up the system prompts for the AI, instructing
78     it on how to generate code and the coding philosophy to adhere to. The constructed prompt
79     consists of the "roadmap", "generate" (with dynamic format replacements), and the coding
80     "philosophy" taken from the given DBs object.
81 
82     Parameters:
83     - dbs (DBs): The database object containing pre-defined prompts and instructions.
84 
85     Returns:
86     - str: The constructed system prompt for the AI.
87     """
88     return (
89         dbs.preprompts["roadmap"]
90         + dbs.preprompts["generate"].replace("FILE_FORMAT", dbs.preprompts["file_format"])
91         + "\nUseful to know:\n"
92         + dbs.preprompts["philosophy"]
93     )
94 
95 
96 def setup_sys_prompt_existing_code(dbs: DBs) -> str:
97     """
98     Constructs a system prompt for the AI focused on improving an existing codebase.
99 
100     This function sets up the system prompts for the AI, guiding it on how to
101     work with and improve an existing code base. The generated prompt consists
102     of the "improve" instruction (with dynamic format replacements) and the coding
103     "philosophy" taken from the given DBs object.
104 
105     Parameters:
106     - dbs (DBs): The database object containing pre-defined prompts and instructions.
107 
108     Returns:
109     - str: The constructed system prompt focused on existing code improvement for the AI.
110     """
111     return (
112         dbs.preprompts["improve"].replace("FILE_FORMAT", dbs.preprompts["file_format"])
113         + "\nUseful to know:\n"
114         + dbs.preprompts["philosophy"]
115     )
</original>
<patched>46 """
47 
48 import inspect
49 import re
50 import subprocess
51 
52 from enum import Enum
53 from typing import List, Union
54 
55 from langchain.schema import AIMessage, HumanMessage, SystemMessage
56 from termcolor import colored
57 
58 from gpt_engineer.core.ai import AI
59 from gpt_engineer.core.chat_to_files import (
60     format_file_to_input,
61     get_code_strings,
62     overwrite_files_with_edits,
63     to_files_and_memory,
64 )
65 from gpt_engineer.core.db import DBs
66 from gpt_engineer.cli.file_selector import FILE_LIST_NAME, ask_for_files
67 from gpt_engineer.cli.learning import human_review_input
68 
69 # Type hint for chat messages
70 Message = Union[AIMessage, HumanMessage, SystemMessage]
71 
72 
73 def setup_sys_prompt(dbs: DBs) -> str:
74     """
75     Constructs a system prompt for the AI based on predefined instructions and philosophies.
76 
77     This function is responsible for setting up the system prompts for the AI, instructing
78     it on how to generate code and the coding philosophy to adhere to. The constructed prompt
79     consists of the "roadmap", "generate" (with dynamic format replacements), and the coding
80     "philosophy" taken from the given DBs object.
81 
82     Parameters:
83     - dbs (DBs): The database object containing pre-defined prompts and instructions.
84 
85     Returns:
86     - str: The constructed system prompt for the AI.
87     """
88     return (
89         dbs.preprompts["roadmap"]
90         + dbs.preprompts["generate"].replace("FILE_FORMAT", dbs.preprompts["file_format"])
91         + "\nUseful to know:\n"
92         + dbs.preprompts["philosophy"]
93     )
94 
95 
96 def setup_sys_prompt_existing_code(dbs: DBs) -> str:
97     """
98     Constructs a system prompt for the AI focused on improving an existing codebase.
99 
100     This function sets up the system prompts for the AI, guiding it on how to
101     work with and improve an existing code base. The generated prompt consists
102     of the "improve" instruction (with dynamic format replacements) and the coding
103     "philosophy" taken from the given DBs object.
104 
105     Parameters:
106     - dbs (DBs): The database object containing pre-defined prompts and instructions.
107 
108     Returns:
109     - str: The constructed system prompt focused on existing code improvement for the AI.
110     """
111     return (
112         dbs.preprompts["improve"].replace("FILE_FORMAT", dbs.preprompts["file_format"])
113         + "\nUseful to know:\n"
114         + dbs.preprompts["philosophy"]
115     )
116
117 def prompt_qa_tasks(dbs: DBs) -> str:
118     """
119     Construct prompt text to ask the LLM what QA tests a QA person would manually perform
120     based on the project specification.
121     """
122     return (
123         "You are a QA engineer. Given the project specification, list the QA tasks "
124         "that a manual QA person would perform to test the generated code. "
125         "Provide the list as bullet points, each bullet being a concise test description.\n\n"
126         "Project specification:\n"
127         + dbs.input["prompt"]
128     )
129
130 def prompt_code_review(qa_task: str, dbs: DBs) -> str:
131     """
132     Construct prompt text to ask the LLM to analyze generated code and QA task,
133     reporting if it seems to pass or fail.
134     """
135     # Aggregate all current generated code as textual context
136     code_text = ""
137     for filename, content in dbs.workspace.items():
138         if isinstance(content, str):
139             code_text += f"\nFilename: {filename}\n{content}\n"
140
141     return (
142         "You are a QA engineer reviewing generated code. "
143         "Given the QA test description and the generated code below, "
144         "answer with either 'PASS' or 'FAIL' and an explanation if it would pass or fail the test.\n\n"
145         f"QA test:\n{qa_task}\n\nGenerated code:\n{code_text}"
146     )
147
148 def prompt_self_heal(failing_task: str, dbs: DBs) -> str:
149     """
150     Construct prompt text to ask the LLM to generate fixes in code blocks for a failing QA task.
151     """
152     # Aggregate all current generated code as textual context
153     code_text = ""
154     for filename, content in dbs.workspace.items():
155         if isinstance(content, str):
156             code_text += f"\nFilename: {filename}\n{content}\n"
157
158     return (
159         "You are a software engineer tasked with fixing a failing QA test.\n"
160         "The QA test failed: " + failing_task + "\n"
161         "Based on the previously generated code, provide improved code in code blocks that overwrite the necessary files to fix the issue.\n"
162         "Only provide the fixed code blocks, do not explain or add text.\n"
163         "\nCode base:\n" + code_text
164     )
165 
166 
167 def review_code(ai: AI, dbs: DBs) -> List[str]:
168     """
169     Ask the LLM to list QA tasks, then check if code passes or fails each, returning failed tasks.
170     """
171     qa_tasks = []
172     # Step 1: Ask for QA tasks
173     qa_prompt = prompt_qa_tasks(dbs)
174     messages = ai.start(qa_prompt, "", step_name="ask_for_qa_tasks")
175     content = messages[-1].content.strip()
176     for line in content.splitlines():
177         line = line.strip()
178         if line.startswith("-") or line.startswith("*"):
179             line = line[1:].strip()
180         if line:
181             qa_tasks.append(line)
182
183     # Step 2: For each QA task, ask if code passes or fails
184     failing_tasks = []
185     for task in qa_tasks:
186         review_prompt = prompt_code_review(task, dbs)
187         messages = ai.start(review_prompt, "", step_name="code_review")
188         resp = messages[-1].content.strip().lower()
189         if "fail" in resp:
190             failing_tasks.append(task)
191     return failing_tasks
192
193 def self_heal_code(ai: AI, dbs: DBs, failing_tasks: List[str]) -> bool:
194     """
195     For each failing QA task, prompts the LLM to generate fixes and overwrites files.
196     Returns True if any fix was applied.
197     """
198     if not failing_tasks:
199         return False
200
201     fixes_applied = False
202     for task in failing_tasks:
203         heal_prompt = prompt_self_heal(task, dbs)
204         messages = ai.start(heal_prompt, "", step_name="self_heal")
205         content = messages[-1].content.strip()
206         overwrite_files_with_edits(content, dbs)
207         fixes_applied = True
208     return fixes_applied
</patched>
```