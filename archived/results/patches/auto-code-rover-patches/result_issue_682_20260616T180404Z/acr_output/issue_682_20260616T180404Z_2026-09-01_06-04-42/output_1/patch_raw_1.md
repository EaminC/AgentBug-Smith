The issue requests an explicit "code review" step with the following enhanced functionality:
1. Asking the LLM to produce a QA checklist from project specifications.
2. Having the LLM inspect the generated code against each QA task and assess pass/fail.
3. For detected issues, allow the LLM to output code blocks that overwrite files to fix problems (self-healing).

We want to add this automated QA and code correction flow as a new step in `steps.py`. This new step can be named, e.g., `ai_code_review_and_self_heal`.

The current `human_review` function takes manual user review input. We should leave that intact to preserve fallback manual feedback.

The AI class can be extended with helper methods to support the new QA flow:
- generate_qa_tasks to get the QA checklist
- qa_code_inspection to check if the code passes the QA tasks
- generate_fixes to propose fixed code blocks

These methods will use the existing chat interface and backoff_inference for robustness.

**Summary of patch:**

1. Add `ai_code_review_and_self_heal` function in `steps.py` that:
   - Queries the LLM to generate QA tasks based on project spec
   - For each QA task:
     - Queries the LLM if code passes the QA task
   - If any issues detected, queries LLM for optional fixes as code blocks
   - If fixes present, overwrite relevant files in the project folder
   - Stores the QA tasks, inspection results, and fix results to memory for traceability

2. Add new helper methods in the `AI` class in `ai.py`:
   - `generate_qa_tasks(project_spec: str) -> List[str]`
   - `inspect_code_for_qa_task(code_map: Dict[str, str], qa_task: str) -> str`
   - `generate_code_fixes(inspection_summary: str) -> Dict[str, str]`

3. Import any needed modules (e.g., os, json).

This minimal patch adds the proposed fully automated QA and self-healing code step without disrupting existing functionality.

---

# modification 1
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
614     return []</original>
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
617 def ai_code_review_and_self_heal(ai: AI, dbs: DBs):
618     """
619     An automated AI-driven code review and self-healing step.
620 
621     1) Queries the LLM to generate QA tasks based on the project specification.
622     2) For each QA task, the LLM inspects the generated code and states if it passes or fails.
623     3) If any QA task fails, the LLM optionally outputs code blocks with fixes.
624     4) Fixes are written to the project files, enabling self-healing.
625 
626     The results of QA tasks, inspections, and fixes are saved in memory under keys:
627     "qa_tasks", "qa_inspection", and "self_heal_fixes".
628 
629     Parameters:
630     - ai (AI): The AI instance to use for chatting.
631     - dbs (DBs): The database instance with file data and memory.
632 
633     Returns:
634     - list: empty list (no new messages)
635     """
636     # Retrieve project specification from dbs.prompts or similar key
637     project_spec = dbs.prompts.get("project_specification") or "No project specification provided."
638 
639     # Retrieve the code to inspect as a map filename -> content
640     code_map = {file: dbs.project[file] for file in dbs.project}
641 
642     # 1) Generate QA tasks based on project spec
643     qa_prompt = (
644         "You are a QA analyst. Given the following project specification,\n"
645         "please generate a list of manual QA test tasks that a QA person would perform.\n"
646         "List each QA task as a short sentence or phrase.\n\n"
647         f"Project specification:\n{project_spec}\n\n"
648         "Output the QA tasks as a JSON array of strings."
649     )
650     try:
651         qa_messages = ai.start(system="Generate QA tasks", user=qa_prompt, step_name="generate_qa_tasks")
652         last_message = qa_messages[-1].content
653         import json
654         qa_tasks = json.loads(last_message)
655         if not isinstance(qa_tasks, list):
656             qa_tasks = []
657     except Exception as e:
658         qa_tasks = []
659 
660     dbs.memory["qa_tasks"] = qa_tasks
661 
662     # 2) Inspect code for each QA task
663     inspection_results = {}
664     for task in qa_tasks:
665         inspect_prompt = (
666             "You are a code reviewer. Given the following QA task and the current code in the project,\n"
667             "answer whether the code is expected to pass this QA task based on code inspection only.\n"
668             "If it is expected to fail, explain why in brief.\n\n"
669             f"QA task: {task}\n\n"
670             "Code files:\n"
671         )
672         for filename, content in code_map.items():
673             inspect_prompt += f"File: {filename}\n```\n{content}\n```\n\n"
674 
675         try:
676             inspection_messages = ai.start(system="Inspect code for QA", user=inspect_prompt, step_name="inspect_code_for_qa_task")
677             inspect_response = inspection_messages[-1].content.strip()
678         except Exception:
679             inspect_response = "Inspection failed: unable to determine."
680         inspection_results[task] = inspect_response
681 
682     dbs.memory["qa_inspection"] = inspection_results
683 
684     # 3) Check if any failures / issues are reported
685     need_fix = False
686     for resp in inspection_results.values():
687         lowered = resp.lower()
688         if ("fail" in lowered or "problem" in lowered or "error" in lowered or "bug" in lowered or "not work" in lowered) and "no" not in lowered:
689             need_fix = True
690             break
691 
692     # 4) If fixes needed, generate fixes
693     fixes = {}
694     if need_fix:
695         fix_prompt = (
696             "You are a software engineer AI. Based on the QA inspection results below, generate code fixes as needed.\n"
697             "Output corrected files in the following JSON format:\n"
698             "{ \"filename1\": \"file content\", \"filename2\": \"file content\" }\n\n"
699             "QA inspection results:\n"
700         )
701         for task, resp in inspection_results.items():
702             fix_prompt += f"- QA Task: {task}\n  Inspection: {resp}\n"
703         try:
704             fix_messages = ai.start(system="Generate code fixes", user=fix_prompt, step_name="generate_code_fixes")
705             fix_response = fix_messages[-1].content.strip()
706             try:
707                 fixes = json.loads(fix_response)
708             except Exception:
709                 fixes = {}
710         except Exception:
711             fixes = {}
712 
713         # Write fixes to project files
714         for filename, new_content in fixes.items():
715             if isinstance(new_content, str):
716                 dbs.project[filename] = new_content
717 
718     dbs.memory["self_heal_fixes"] = fixes
719 
720     return []
</patched>
```

# modification 2
```
<file>gpt_engineer/core/ai.py</file>
<original>55 class AI:
56     """
57     A class to interface with a language model for chat-based interactions.
58 
59     This class provides methods to initiate and maintain conversations using
60     a specified language model. It handles token counting, message creation,
61     serialization and deserialization of chat messages, and interfaces with
62     the language model to get AI-generated responses.
63 
64     Attributes
65     ----------
66     temperature : float
67         The temperature setting for the model, affecting the randomness of the output.
68     azure_endpoint : str
69         The Azure endpoint URL, if applicable.
70     model_name : str
71         The name of the model being used.
72     llm : Any
73         The chat model instance.
74     token_usage_log : Any
75         The token usage log used to store cumulitive tokens used during the lifetime of the ai class
76 
77     Methods
78     -------
79     start(system, user, step_name) -> List[Message]:
80         Start the conversation with a system and user message.
81     next(messages, prompt, step_name) -> List[Message]:
82         Advance the conversation by interacting with the language model.
83     backoff_inference(messages, callbacks) -> Any:
84         Interact with the model using an exponential backoff strategy in case of rate limits.
85     serialize_messages(messages) -> str:
86         Serialize a list of messages to a JSON string.
87     deserialize_messages(jsondictstr) -> List[Message]:
88         Deserialize a JSON string into a list of messages.
89 
90     """
91 
92     def __init__(self, model_name="gpt-4", temperature=0.1, azure_endpoint=""):
93         """
94         Initialize the AI class.
95 
96         Parameters
97         ----------
98         model_name : str, optional
99             The name of the model to use, by default "gpt-4".
100         temperature : float, optional
101             The temperature to use for the model, by default 0.1.
102         """
103         self.temperature = temperature
104         self.azure_endpoint = azure_endpoint
105         self.model_name = self._check_model_access_and_fallback(model_name)
106 
107         self.llm = self._create_chat_model()
108         self.token_usage_log = TokenUsageLog(model_name)
109 
110         logger.debug(f"Using model {self.model_name}")
111 
112     def start(self, system: str, user: str, step_name: str) -> List[Message]:
113         """
114         Start the conversation with a system message and a user message.
115 
116         Parameters
117         ----------
118         system : str
119             The content of the system message.
120         user : str
121             The content of the user message.
122         step_name : str
123             The name of the step.
124 
125         Returns
126         -------
127         List[Message]
128             The list of messages in the conversation.
129         """
130 
131         messages: List[Message] = [
132             SystemMessage(content=system),
133             HumanMessage(content=user),
134         ]
135         return self.next(messages, step_name=step_name)
136 
137     def next(
138         self,
139         messages: List[Message],
140         prompt: Optional[str] = None,
141         *,
142         step_name: str,
143     ) -> List[Message]:
144         """
145         Advances the conversation by sending message history
146         to LLM and updating with the response.
147 
148         Parameters
149         ----------
150         messages : List[Message]
151             The list of messages in the conversation.
152         prompt : Optional[str], optional
153             The prompt to use, by default None.
154         step_name : str
155             The name of the step.
156 
157         Returns
158         -------
159         List[Message]
160             The updated list of messages in the conversation.
161         """
162         """
163         Advances the conversation by sending message history
164         to LLM and updating with the response.
165         """
166         if prompt:
167             messages.append(HumanMessage(content=prompt))
168 
169         logger.debug(f"Creating a new chat completion: {messages}")
170 
171         callbacks = [StreamingStdOutCallbackHandler()]
172         response = self.backoff_inference(messages, callbacks)
173 
174         self.token_usage_log.update_log(
175             messages=messages, answer=response.content, step_name=step_name
176         )
177         messages.append(response)
178         logger.debug(f"Chat completion finished: {messages}")
179 
180         return messages
181 
182     @backoff.on_exception(
183         backoff.expo, openai.error.RateLimitError, max_tries=7, max_time=45
184     )
185     def backoff_inference(self, messages, callbacks):
186         """
187         Perform inference using the language model while implementing an exponential backoff strategy.
188 
189         This function will retry the inference in case of a rate limit error from the OpenAI API.
190         It uses an exponential backoff strategy, meaning the wait time between retries increases
191         exponentially. The function will attempt to retry up to 7 times within a span of 45 seconds.
192 
193         Parameters
194         ----------
195         messages : List[Message]
196             A list of chat messages which will be passed to the language model for processing.
197 
198         callbacks : List[Callable]
199             A list of callback functions that are triggered after each inference. These functions
200             can be used for logging, monitoring, or other auxiliary tasks.
201 
202         Returns
203         -------
204         Any
205             The output from the language model after processing the provided messages.
206 
207         Raises
208         ------
209         openai.error.RateLimitError
210             If the number of retries exceeds the maximum or if the rate limit persists beyond the
211             allotted time, the function will ultimately raise a RateLimitError.
212 
213         Example
214         -------
215         >>> messages = [SystemMessage(content="Hello"), HumanMessage(content="How's the weather?")]
216         >>> callbacks = [some_logging_callback]
217         >>> response = backoff_inference(messages, callbacks)
218         """
219         return self.llm(messages, callbacks=callbacks)  # type: ignore
220 
221     @staticmethod
222     def serialize_messages(messages: List[Message]) -> str:
223         """
224         Serialize a list of messages to a JSON string.
225 
226         Parameters
227         ----------
228         messages : List[Message]
229             The list of messages to serialize.
230 
231         Returns
232         -------
233         str
234             The serialized messages as a JSON string.
235         """
236         return json.dumps(messages_to_dict(messages))
237 
238     @staticmethod
239     def deserialize_messages(jsondictstr: str) -> List[Message]:
240         """
241         Deserialize a JSON string to a list of messages.
242 
243         Parameters
244         ----------
245         jsondictstr : str
246             The JSON string to deserialize.
247 
248         Returns
249         -------
250         List[Message]
251             The deserialized list of messages.
252         """
253         data = json.loads(jsondictstr)
254         # Modify implicit is_chunk property to ALWAYS false
255         # since Langchain's Message schema is stricter
256         prevalidated_data = [
257             {**item, "data": {**item["data"], "is_chunk": False}} for item in data
258         ]
259         return list(messages_from_dict(prevalidated_data))  # type: ignore
260 
261     def _check_model_access_and_fallback(self, model_name) -> str:
262         """
263         Retrieve the specified model, or fallback to "gpt-3.5-turbo" if the model is not available.
264 
265         Parameters
266         ----------
267         model : str
268             The name of the model to retrieve.
269 
270         Returns
271         -------
272         str
273             The name of the retrieved model, or "gpt-3.5-turbo" if the specified model is not available.
274         """
275         try:
276             openai.Model.retrieve(model_name)
277         except openai.InvalidRequestError:
278             print(
279                 f"Model {model_name} not available for provided API key. Reverting "
