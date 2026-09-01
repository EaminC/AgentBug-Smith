Reasoning:
To implement the explicit "code review" step with self-healing via the LLM, the best approach is to add a new step function in the steps.py file that does the following:
1. Uses the AI instance to first generate a list of QA tasks from the project specification (from dbs.project_spec).
2. Then iteratively asks the LLM to evaluate whether the generated code would pass or fail each QA task by inspecting the code.
3. If any QA task fails or a problem is detected, prompt the LLM to generate code block fixes to self-heal the codebase by overwriting files accordingly.
4. Update the memory or file system with those fixes.
5. Return a summary list of QA results and applied fixes.

This new function can be called something like llm_code_review_with_self_healing. It should be added without removing the existing human_review step, so manual human review remains optionally available.

Additionally, helper methods implementing the above LLM interactions should be encapsulated in the AI class to cleanly integrate with the existing LLM interaction methods. This means:
- Adding in AI class methods to produce the QA checklist from the spec.
- To analyze the generated code against each QA task.
- To produce fixes if issues are found.

No changes needed to the human_review_input function in learning.py, as it handles manual user input well and can remain for manual review fallback.

The patch will:
- Add new AI methods: generate_qa_tasks, evaluate_qa_task, generate_self_healing_code.
- Add a new step function llm_code_review_with_self_healing in steps.py.
- This new step uses those AI methods to realize the explicit LLM QA + self healing.

---

Patch:

```
<file>gpt_engineer/core/steps.py</file>
<original>586 def human_review(ai: AI, dbs: DBs):
587     """
588     Collects human feedback on the code and stores it in memory.
589 
590     This function prompts the user for a review of the generated or improved code using the `human_review_input`
591     function. If a valid review is provided, it's serialized to JSON format and stored within the database's
592     memory under the "review" key.
593 
594     Parameters:
595     - ai (AI): An instance of the AI model. Although not directly used within the function, it is kept as
596       a parameter for consistency with other functions.
597     - dbs (DBs): An instance containing the database configurations, user prompts, project metadata,
598       and memory storage. This function specifically interacts with the memory storage to save the human review.
599 
600     Returns:
601     - list: Returns an empty list, indicating that there's no subsequent interaction with the LLM
602       or no further messages to be processed.
603 
604     Notes:
605     - It's assumed that the `human_review_input` function handles all the interactions with the user to
606       gather feedback and returns either the feedback or None if no feedback was provided.
607     - Ensure that the database's memory has enough space or is set up correctly to store the serialized review data.
608     """
609 
610     """Collects and stores human review of the code"""
611     review = human_review_input()
612     if review is not None:
613         dbs.memory["review"] = review.to_json()  # type: ignore
614     return []
</original>
<patched>586 def human_review(ai: AI, dbs: DBs):
587     """
588     Collects human feedback on the code and stores it in memory.
589 
590     This function prompts the user for a review of the generated or improved code using the `human_review_input`
591     function. If a valid review is provided, it's serialized to JSON format and stored within the database's
592     memory under the "review" key.
593 
594     Parameters:
595     - ai (AI): An instance of the AI model. Although not directly used within the function, it is kept as
596       a parameter for consistency with other functions.
597     - dbs (DBs): An instance containing the database configurations, user prompts, project metadata,
598       and memory storage. This function specifically interacts with the memory storage to save the human review.
599 
600     Returns:
601     - list: Returns an empty list, indicating that there's no subsequent interaction with the LLM
602       or no further messages to be processed.
603 
604     Notes:
605     - It's assumed that the `human_review_input` function handles all the interactions with the user to
606       gather feedback and returns either the feedback or None if no feedback was provided.
607     - Ensure that the database's memory has enough space or is set up correctly to store the serialized review data.
608     """
609 
610     """Collects and stores human review of the code"""
611     review = human_review_input()
612     if review is not None:
613         dbs.memory["review"] = review.to_json()  # type: ignore
614     return []
615 
616 
617 def llm_code_review_with_self_healing(ai: AI, dbs: DBs) -> list:
618     """
619     Performs an explicit LLM-driven code review with QA task generation,
620     code inspection, and optional self-healing by generating code fixes.
621 
622     Steps:
623     1. Generate a list of QA tasks based on the project specification using the LLM.
624     2. For each QA task, ask the LLM to inspect the generated code to assess if the code is expected to pass or fail.
625     3. If problems are detected, ask the LLM to generate self-healing code blocks to fix the issues.
626     4. Overwrite the relevant files with fixes.
627     5. Save QA results and fixes summaries to memory.
628 
629     Parameters:
630     - ai (AI): The AI instance for communicating with the LLM.
631     - dbs (DBs): The database instance including project specs and file system.
632 
633     Returns:
634     - List of QA task results and any applied fix summaries.
635     """
636 
637     # Step 1: Generate QA tasks from project spec
638     project_spec = dbs.project_spec
639     qa_tasks = ai.generate_qa_tasks(project_spec)
640 
641     qa_results = []
642     fixes_applied = []
643 
644     for task in qa_tasks:
645         # Step 2: Evaluate the generated code for the QA task
646         evaluation = ai.evaluate_qa_task(task, dbs)
647         qa_results.append({"task": task, "result": evaluation["result"], "details": evaluation.get("details", "")})
648 
649         # Step 3: If failed or broken, generate self healing code blocks/fixes
650         if evaluation["result"].lower() != "pass":
651             fixes = ai.generate_self_healing_code(task, dbs, evaluation.get("details", ""))
652             for fix in fixes:
653                 filename = fix["filename"]
654                 content = fix["content"]
655                 # Overwrite file in dbs filesystem
656                 dbs.file_system.write_text(filename, content)
657                 fixes_applied.append(fix)
658 
659     # Save results and fixes summaries in memory for review or reporting
660     dbs.memory["llm_qa_results"] = json.dumps(qa_results)
661     dbs.memory["llm_fixes_applied"] = json.dumps(fixes_applied)
662 
663     summary = {
664         "qa_results": qa_results,
665         "fixes_applied": fixes_applied,
666     }
667 
668     return [summary]
</patched>
</file>

```

```
<file>gpt_engineer/core/ai.py</file>
<original>55 class AI:
56     """
57     A class to interface with a language model for chat-based interactions.
...
286 
287     def _create_chat_model(self) -> BaseChatModel:
288         """
289         Create a chat model with the specified model name and temperature.
290 
291         Parameters
292         ----------
293         model : str
294             The name of the model to create.
295         temperature : float
296             The temperature to use for the model.
297 
298         Returns
299         -------
300         BaseChatModel
301             The created chat model.
302         """
303         if self.azure_endpoint:
304             return AzureChatOpenAI(
305                 openai_api_base=self.azure_endpoint,
306                 openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
307                 deployment_name=self.model_name,
308                 openai_api_type="azure",
309                 streaming=True,
310             )
311 
312         return ChatOpenAI(
313             model=self.model_name,
314             temperature=self.temperature,
315             streaming=True,
316             client=openai.ChatCompletion,
317         )</original>
<patched>55 class AI:
56     """
57     A class to interface with a language model for chat-based interactions.
...
286 
287     def _create_chat_model(self) -> BaseChatModel:
288         """
289         Create a chat model with the specified model name and temperature.
290 
291         Parameters
292         ----------
293         model : str
294             The name of the model to create.
295         temperature : float
296             The temperature to use for the model.
297 
298         Returns
299         -------
300         BaseChatModel
301             The created chat model.
302         """
303         if self.azure_endpoint:
304             return AzureChatOpenAI(
305                 openai_api_base=self.azure_endpoint,
306                 openai_api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
307                 deployment_name=self.model_name,
308                 openai_api_type="azure",
309                 streaming=True,
310             )
311 
312         return ChatOpenAI(
313             model=self.model_name,
314             temperature=self.temperature,
315             streaming=True,
316             client=openai.ChatCompletion,
317         )
318 
319     def generate_qa_tasks(self, project_spec: str) -> list:
320         """
321         Use the LLM to generate a list of QA tasks based on the project specification.
322 
323         Parameters:
324         - project_spec (str): The project specification description.
325 
326         Returns:
327         - List[str]: A list of QA task descriptions.
328         """
329         prompt = (
330             "You are a QA engineer. Based on the following project specification, generate a list of specific, "
331             "manual QA tasks that a human QA tester would perform to verify the correctness of the generated code. "
332             "Return the tasks as a bullet list, no explanations.\n\n"
333             f"Project specification:\n{project_spec}\n\nQA Tasks:"
334         )
335         response_messages = self.next([], prompt=prompt, step_name="generate_qa_tasks")
336         content = response_messages[-1].content.strip()
337 
338         # Parse bullet-list tasks (assume each line starts with a bullet)
339         tasks = []
340         for line in content.splitlines():
341             line = line.strip()
342             if line and (line.startswith("-") or line.startswith("*")):
343                 task = line[1:].strip()
344                 if task:
345                     tasks.append(task)
346         return tasks
347 
348     def evaluate_qa_task(self, qa_task: str, dbs: "DBs") -> dict:
349         """
350         Ask the LLM to inspect the generated code and assess if it would pass the QA task.
351 
352         Parameters:
353         - qa_task (str): The QA task description.
354         - dbs (DBs): Database interface to read the current generated code files.
355 
356         Returns:
357         - dict with keys 'result' (str: "Pass" or "Fail") and optionally 'details' (str explanation).
358         """
359         # Read relevant generated code as concatenated string
360         all_code = []
361         for filename, filemeta in dbs.file_system.all_files.items():
362             # Read only text/code files (skip binary if necessary)
363             try:
364                 content = dbs.file_system.read_text(filename)
365                 all_code.append(f"Filename: {filename}\n{content}\n")
366             except Exception:
367                 pass
368         code_context = "\n".join(all_code)
369 
370         prompt = (
371             "You are a QA engineer reviewing generated code. For the following QA task, "
372             "inspect the provided code and determine if the task is passed or failed. "
373             "Answer with only 'Pass' or 'Fail' on the first line, then optionally provide a brief explanation.\n\n"
374             f"QA Task: {qa_task}\n\n"
375             "Code:\n"
376             f"{code_context}\n\nResult:"
377         )
378         response_messages = self.next([], prompt=prompt, step_name="evaluate_qa_task")
379         content = response_messages[-1].content.strip()
380         lines = content.splitlines()
381         result = lines[0].strip().lower()
382         if result == "pass":
383             return {"result": "Pass"}
384         elif result == "fail":
385             details = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
386             return {"result": "Fail", "details": details}
387         else:
388             # Unexpected answer, assume fail with explanation
389             return {"result": "Fail", "details": content}
390 
391     def generate_self_healing_code(self, qa_task: str, dbs: "DBs", details: str) -> list:
392         """
393         Ask the LLM to generate code blocks that fix the problem described in the QA task.
394 
395         Parameters:
396         - qa_task (str): The QA task description for which fix is required.
397         - dbs (DBs): The database interface to read current files.
398         - details (str): Explanation of what went wrong, if any.
399 
400         Returns:
401         - List of dicts with keys 'filename' and 'content' representing files to overwrite with fixed code.
402         """
403         # Read current files to provide context
404         all_code = []
405         for filename, filemeta in dbs.file_system.all_files.items():
406             try:
407                 content = dbs.file_system.read_text(filename)
408                 all_code.append(f"Filename: {filename}\n{content}\n")
409             except Exception:
410                 pass
411         code_context = "\n".join(all_code)
412 
413         prompt = (
414             "You are a helpful software engineer instructed to fix broken code based on QA task failure.\n"
415             f"QA Task: {qa_task}\n"
416             f"Failure details: {details}\n\n"
417             "The following is the current project code:\n"
418             f"{code_context}\n\n"
419             "Please provide a list of filenames and corresponding code blocks to fix the issues."
420             " Structure the response with markdown style code blocks as below:\n\n"
421             "```filename\n"
422             "code content\n"
423             "```\n\n"
424             "Only provide these code blocks with filenames indicating which file to overwrite.\n"
425         )
426         response_messages = self.next([], prompt=prompt, step_name="generate_self_healing_code")
427         content = response_messages[-1].content.strip()
428 
429         # Extract code blocks of form ```filename\ncode\n```
430         import re
431         pattern = r"```([\w\.\/\-]+)\n(.*?)```"
432         matches = re.findall(pattern, content, re.DOTALL)
433 
434         fixes = []
435         for filename, code in matches:
436             fixes.append({"filename": filename.strip(), "content": code.strip()})
437 
438         return fixes
</patched>
</file>
```