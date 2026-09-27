The issue is a feature request to add an explicit "code review" step that uses the LLM to identify QA tasks that a human tester would perform, to analyze the generated code for expected pass/fail of these QA tasks, and then optionally auto-generate fixes in code blocks to self-heal or repair failing code. This requires extending the existing Review class to support these capabilities and adding functions to integrate these AI-driven review steps into the workflows.

The relevant files for the implementation are:
- `gpt_engineer/cli/learning.py` => extend Review class with methods for review prompts, QA task extraction, code QA assessment, and fix generation.
- `gpt_engineer/core/steps.py` => add helper functions to manage these review/self-healing prompts and integrate them into the step system if needed.

The Review class is currently a simple dataclass holding review metadata. We should add methods that:
- generate a prompt to ask the LLM what QA tasks a human tester would perform
- a method to query the LLM whether the code is expected to pass each QA task or if something is broken
- a method to prompt the LLM to output code blocks with fixes to apply, to overwrite files if needed

These methods should use the provided instructions and be callable with an AI and DBs object context.

In steps.py, we can add helper functions to orchestrate these review steps if it's desirable to have explicit step functions to drive the review self-healing cycle.

This patch therefore:
- adds methods to `Review` in `learning.py`
- adds prompt assembly functions in `steps.py` to ask for QA task list, ask for review QA pass/fail evaluation, and get fixes
- defines a step `review_and_fix_code` in steps.py that runs this cycle

This patch does minimal changes preserving existing code and extends functionality as requested.

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
<patched>61 class Review:
62     ran: Optional[bool]
63     perfect: Optional[bool]
64     works: Optional[bool]
65     comments: str
66     raw: str
67
68     def generate_qa_tasks_prompt(self, project_specification: str) -> str:
69         """
70         Generates a prompt to ask the LLM what QA tasks a human tester would perform based on the project specification.
71
72         Returns:
73             str: The LLM prompt to generate QA tasks.
74         """
75         prompt = (
76             f"Given the following project specification:\n{project_specification}\n\n"
77             "List the main QA tasks that a human tester would perform to validate if the code works as expected.\n"
78             "Provide each QA task as a short itemized statement.\n"
79         )
80         return prompt
81
82     def generate_code_qa_assessment_prompt(self, code_snippet: str, qa_tasks: list[str]) -> str:
83         """
84         Generates a prompt to ask the LLM to assess if the generated code is expected to pass each QA task,
85         or if something seems broken, by inspecting the code.
86
87         Parameters:
88             code_snippet (str): The code to be inspected.
89             qa_tasks (list[str]): The list of QA tasks to check against the code.
90
91         Returns:
92             str: The LLM prompt to perform code QA assessment.
93         """
94         qa_tasks_text = "\n".join(f"- {task}" for task in qa_tasks)
95         prompt = (
96             "You are performing a code review by inspecting the generated code below.\n\n"
97             "Code:\n"
98             f"{code_snippet}\n\n"
99             "QA tasks to verify:\n"
100             f"{qa_tasks_text}\n\n"
101             "For each QA task, answer whether the code is expected to pass it. "
102             "If it seems the code will fail or has issues related to the task, explain briefly.\n"
103             "Format your response as an itemized list with pass/fail and comments.\n"
104         )
105         return prompt
106
107     def generate_fix_code_prompt(self, code_snippet: str, failed_tasks_comments: str) -> str:
108         """
109         Generates a prompt to ask the LLM to output code blocks that overwrite files to fix the problems detected.
110
111         Parameters:
112             code_snippet (str): The original generated code.
113             failed_tasks_comments (str): The comments describing issues found in the QA assessment.
114
115         Returns:
116             str: The LLM prompt that instructs it to generate fixing code blocks.
117         """
118         prompt = (
119             "The following code has been found to have issues based on QA review:\n\n"
120             f"{code_snippet}\n\n"
121             "Issues found:\n"
122             f"{failed_tasks_comments}\n\n"
123             "Please provide corrected code snippets in markdown code blocks to fix these issues. "
124             "For each code block, specify the filename and the updated content so it can be applied to the codebase."
125         )
126         return prompt
</patched>
```

# modification 2
```
<file>gpt_engineer/core/steps.py</file>
<original>47 
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
70 Message = Union[AIMessage, HumanMessage, SystemMessage]</original>
<patched>47 
48 import inspect
49 import re
50 import subprocess
51
52 from enum import Enum
53 from typing import List, Union, Optional
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
67 from gpt_engineer.cli.learning import human_review_input, Review
68
69 # Type hint for chat messages
70 Message = Union[AIMessage, HumanMessage, SystemMessage]

# New helper functions related to explicit code review & self healing

def generate_review_qa_tasks(ai: AI, dbs: DBs, project_specification: str) -> List[str]:
    """
    Ask the LLM to generate a list of QA tasks that a human tester would do, based on the project specification.
    """
    review = Review(ran=None, perfect=None, works=None, comments="", raw="")
    prompt = review.generate_qa_tasks_prompt(project_specification)
    messages = ai.start(prompt, "", step_name="generate_review_qa_tasks")
    # We assume each line is a QA task, possibly numbered or with '-'
    raw_text = messages[-1].content.strip()
    # Extract lines that look like tasks, e.g. "- task" or "1. task"
    tasks = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            # Remove common leading list markers
            line = re.sub(r"^(\d+\.|\-|\*)\s*", "", line)
            tasks.append(line)
    return tasks

def review_code_for_qa(ai: AI, dbs: DBs, code_snippet: str, qa_tasks: List[str]) -> str:
    """
    Ask the LLM to review the code for the given QA tasks and return an assessment string.
    """
    review = Review(ran=None, perfect=None, works=None, comments="", raw="")
    prompt = review.generate_code_qa_assessment_prompt(code_snippet, qa_tasks)
    messages = ai.start(prompt, "", step_name="review_code_for_qa")
    return messages[-1].content.strip()

def generate_fix_code_blocks(ai: AI, dbs: DBs, code_snippet: str, issues_found: str) -> str:
    """
    Ask the LLM to output code blocks for fixing the detected issues.
    """
    review = Review(ran=None, perfect=None, works=None, comments="", raw="")
    prompt = review.generate_fix_code_prompt(code_snippet, issues_found)
    messages = ai.start(prompt, "", step_name="generate_fix_code_blocks")
    return messages[-1].content.strip()

def review_and_fix_code(ai: AI, dbs: DBs) -> List[Message]:
    """
    Perform an explicit code review step and optionally self-heal the code if fixes are provided.
    """
    # Read the project specification that defines what should be tested. We use dbs.input['prompt'] which usually is the spec.
    project_specification = dbs.input.get("prompt", "")
    if not project_specification:
        print("No project specification found for QA tasks generation.")
        return []

    # Read current generated code as a large combined string (all files joined)
    code_strings = get_code_strings(dbs.workspace, dbs.project_metadata)
    combined_code = "\n\n".join(f"# File: {fname}\n{contents}" for fname, contents in code_strings.items())

    # Step 1: Ask LLM what QA tasks a human tester would manually test based on spec
    qa_tasks = generate_review_qa_tasks(ai, dbs, project_specification)
    if not qa_tasks:
        print("No QA tasks were generated by the LLM.")
        return []

    # Step 2: For each QA task, ask the LLM if generated code is expected to pass or if something is broken
    assessment = review_code_for_qa(ai, dbs, combined_code, qa_tasks)
    print("\n[Code QA Assessment]\n", assessment)

    # Step 3: If issues found, ask LLM to output code blocks that overwrite files to fix
    # Here a heuristic: if words like "fail", "broken", "not pass" etc appear in assessment, consider fixes needed
    lower_assess = assessment.lower()
    if any(word in lower_assess for word in ["fail", "broken", "error", "incorrect", "problem", "issue", "bug"]):
        print("\n[Detected issues, requesting fixes from LLM...]")
        fixed_code_blocks = generate_fix_code_blocks(ai, dbs, combined_code, assessment)
        print("\n[Fix Code Blocks]\n", fixed_code_blocks)
        # Attempt to apply the fixes from the code blocks returned by LLM
        overwrite_files_with_edits(fixed_code_blocks, dbs)
    else:
        print("No significant issues detected by the review step. No fixes applied.")

    return []
</patched>
```