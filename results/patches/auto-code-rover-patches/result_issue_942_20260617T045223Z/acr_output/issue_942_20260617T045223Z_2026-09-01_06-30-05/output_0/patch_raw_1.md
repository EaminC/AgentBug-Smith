The issue is that the application defaults to using GPT-3.5 Turbo model even though the user has an OpenAI API key that supports GPT-4 usage and did not pass the `--gpt3only` flag. To fix this, we need to:

1. Modify `run_auto_gpt` in `main.py` to respect the `--gpt3only` and `--gpt4only` flags and set the model in Config accordingly. If no flags are passed, default to GPT-4 by setting `fast_llm_model = gpt-4`.

2. Modify `Agent.start_interaction_loop()` to stop hardcoding the model and instead use `cfg.fast_llm_model` when calling `chat_with_ai`.

3. Modify `chat_with_ai` function signature and implementation in `llm/chat.py` to accept an explicit model argument and use it for the chat completion call instead of relying on the fixed attribute in `Config`.

This will ensure the model choice is consistent throughout the runtime, respects user command line flags, and the usage of GPT-4 will become the default behavior when no restrictions are set.

---

# Patch

```
<file>autogpt/main.py</file>
<original>26 def run_auto_gpt(
27     continuous: bool,
28     continuous_limit: int,
29     ai_settings: str,
30     prompt_settings: str,
31     skip_reprompt: bool,
32     speak: bool,
33     debug: bool,
34     gpt3only: bool,
35     gpt4only: bool,
36     memory_type: str,
37     browser_name: str,
38     allow_downloads: bool,
39     skip_news: bool,
40     workspace_directory: str,
41     install_plugin_deps: bool,
42 ):
43     # Configure logging before we do anything else.
44     logger.set_level(logging.DEBUG if debug else logging.INFO)
45     logger.speak_mode = speak
46 
47     cfg = Config()
48     # TODO: fill in llm values here
49     check_openai_api_key()</original>
<patched>26 def run_auto_gpt(
27     continuous: bool,
28     continuous_limit: int,
29     ai_settings: str,
30     prompt_settings: str,
31     skip_reprompt: bool,
32     speak: bool,
33     debug: bool,
34     gpt3only: bool,
35     gpt4only: bool,
36     memory_type: str,
37     browser_name: str,
38     allow_downloads: bool,
39     skip_news: bool,
40     workspace_directory: str,
41     install_plugin_deps: bool,
42 ):
43     # Configure logging before we do anything else.
44     logger.set_level(logging.DEBUG if debug else logging.INFO)
45     logger.speak_mode = speak
46 
47     cfg = Config()
48     # Set model accordingly to CLI flags: default to GPT-4 if no flags provided
49     if gpt3only:
50         cfg.set_fast_llm_model("gpt-3.5-turbo-0301")
51     elif gpt4only:
52         cfg.set_fast_llm_model("gpt-4")
53     else:
54         # Default to gpt-4 if neither flag is provided
55         cfg.set_fast_llm_model("gpt-4")
56 
57     check_openai_api_key()</patched>
```

```
<file>autogpt/agent/agent.py</file>
<original>86     def start_interaction_loop(self):
87         # Interaction Loop
88         cfg = Config()
89         self.cycle_count = 0
90         command_name = None
91         arguments = None
92         user_input = ""
93 
94         # Signal handler for interrupting y -N
95         def signal_handler(signum, frame):
96             if self.next_action_count == 0:
97                 sys.exit()
98             else:
99                 print(
100                     Fore.RED
101                     + "Interrupt signal received. Stopping continuous command execution."
102                     + Style.RESET_ALL
103                 )
104                 self.next_action_count = 0
105 
106         signal.signal(signal.SIGINT, signal_handler)
107 
108         while True:
109             # Discontinue if continuous limit is reached
110             self.cycle_count += 1
111             self.log_cycle_handler.log_count_within_cycle = 0
112             self.log_cycle_handler.log_cycle(
113                 self.config.ai_name,
114                 self.created_at,
115                 self.cycle_count,
116                 [m.raw() for m in self.history],
117                 FULL_MESSAGE_HISTORY_FILE_NAME,
118             )
119             if (
120                 cfg.continuous_mode
121                 and cfg.continuous_limit > 0
122                 and self.cycle_count > cfg.continuous_limit
123             ):
124                 logger.typewriter_log(
125                     "Continuous Limit Reached: ", Fore.YELLOW, f"{cfg.continuous_limit}"
126                 )
127                 break
128             # Send message to AI, get response
129             with Spinner("Thinking... ", plain_output=cfg.plain_output):
130                 assistant_reply = chat_with_ai(
131                     self,
132                     self.system_prompt,
133                     self.triggering_prompt,
134                     cfg.fast_token_limit,
135                 )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument
136 
137             assistant_reply_json = fix_json_using_multiple_techniques(assistant_reply)
138             for plugin in cfg.plugins:
139                 if not plugin.can_handle_post_planning():
140                     continue
141                 assistant_reply_json = plugin.post_planning(assistant_reply_json)
142 
143             # Print Assistant thoughts
144             if assistant_reply_json != {}:
145                 validate_json(assistant_reply_json, LLM_DEFAULT_RESPONSE_FORMAT)
146                 # Get command name and arguments
147                 try:
148                     print_assistant_thoughts(
149                         self.ai_name, assistant_reply_json, cfg.speak_mode
150                     )
151                     command_name, arguments = get_command(assistant_reply_json)
152                     if cfg.speak_mode:
153                         say_text(f"I want to execute {command_name}")
154 
155                     arguments = self._resolve_pathlike_command_args(arguments)
156 
157                 except Exception as e:
158                     logger.error("Error: \n", str(e))
159             self.log_cycle_handler.log_cycle(
160                 self.config.ai_name,
161                 self.created_at,
162                 self.cycle_count,
163                 assistant_reply_json,
164                 NEXT_ACTION_FILE_NAME,
165             )
166 
167             logger.typewriter_log(
168                 "NEXT ACTION: ",
169                 Fore.CYAN,
170                 f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
171                 f"ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
172             )</original>
<patched>86     def start_interaction_loop(self):
87         # Interaction Loop
88         cfg = Config()
89         self.cycle_count = 0
90         command_name = None
91         arguments = None
92         user_input = ""
93 
94         # Signal handler for interrupting y -N
95         def signal_handler(signum, frame):
96             if self.next_action_count == 0:
97                 sys.exit()
98             else:
99                 print(
100                     Fore.RED
101                     + "Interrupt signal received. Stopping continuous command execution."
102                     + Style.RESET_ALL
103                 )
104                 self.next_action_count = 0
105 
106         signal.signal(signal.SIGINT, signal_handler)
107 
108         while True:
109             # Discontinue if continuous limit is reached
110             self.cycle_count += 1
111             self.log_cycle_handler.log_count_within_cycle = 0
112             self.log_cycle_handler.log_cycle(
113                 self.config.ai_name,
114                 self.created_at,
115                 self.cycle_count,
116                 [m.raw() for m in self.history],
117                 FULL_MESSAGE_HISTORY_FILE_NAME,
118             )
119             if (
120                 cfg.continuous_mode
121                 and cfg.continuous_limit > 0
122                 and self.cycle_count > cfg.continuous_limit
123             ):
124                 logger.typewriter_log(
125                     "Continuous Limit Reached: ", Fore.YELLOW, f"{cfg.continuous_limit}"
126                 )
127                 break
128             # Send message to AI, get response
129             with Spinner("Thinking... ", plain_output=cfg.plain_output):
130                 assistant_reply = chat_with_ai(
131                     self,
132                     self.system_prompt,
133                     self.triggering_prompt,
134                     cfg.fast_token_limit,
135                     cfg.fast_llm_model,
136                 )
137 
138             assistant_reply_json = fix_json_using_multiple_techniques(assistant_reply)
139             for plugin in cfg.plugins:
140                 if not plugin.can_handle_post_planning():
141                     continue
142                 assistant_reply_json = plugin.post_planning(assistant_reply_json)
143 
144             # Print Assistant thoughts
145             if assistant_reply_json != {}:
146                 validate_json(assistant_reply_json, LLM_DEFAULT_RESPONSE_FORMAT)
147                 # Get command name and arguments
148                 try:
149                     print_assistant_thoughts(
150                         self.ai_name, assistant_reply_json, cfg.speak_mode
151                     )
152                     command_name, arguments = get_command(assistant_reply_json)
153                     if cfg.speak_mode:
154                         say_text(f"I want to execute {command_name}")
155 
156                     arguments = self._resolve_pathlike_command_args(arguments)
157 
158                 except Exception as e:
159                     logger.error("Error: \n", str(e))
160             self.log_cycle_handler.log_cycle(
161                 self.config.ai_name,
162                 self.created_at,
163                 self.cycle_count,
164                 assistant_reply_json,
165                 NEXT_ACTION_FILE_NAME,
166             )
167 
168             logger.typewriter_log(
169                 "NEXT ACTION: ",
170                 Fore.CYAN,
171                 f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
172                 f"ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
173             )</patched>
```

```
<file>autogpt/llm/chat.py</file>
<original>20 def chat_with_ai(
21     agent: Agent,
22     system_prompt: str,
23     user_input: str,
24     token_limit: int,
25 ):
26     """
27     Interact with the OpenAI API, sending the prompt, user input,
28         message history, and permanent memory.
29 
30     Args:
31         system_prompt (str): The prompt explaining the rules to the AI.
32         user_input (str): The input from the user.
33         token_limit (int): The maximum number of tokens allowed in the API call.
34 
35     Returns:
36     str: The AI's response.
37     """
38     model = cfg.fast_llm_model  # TODO: Change model from hardcode to argument
39     # Reserve 1000 tokens for the response
40     logger.debug(f"Token limit: {token_limit}")
41     send_token_limit = token_limit - 1000
42 
43     # if len(agent.history) == 0:
44     #     relevant_memory = ""
45     # else:
46     #     recent_history = agent.history[-5:]
47     #     shuffle(recent_history)
48     #     relevant_memories = agent.memory.get_relevant(
49     #         str(recent_history), 5
50     #     )
51     #     if relevant_memories:
52     #         shuffle(relevant_memories)
53     #     relevant_memory = str(relevant_memories)
54     # logger.debug(f"Memory Stats: {agent.memory.get_stats()}")
55     relevant_memory = []
56 
57     message_sequence = ChatSequence.for_model(
58         model,
59         [
60             Message("system", system_prompt),
61             Message("system", f"The current time and date is {time.strftime('%c')}"),
62             # Message(
63             #     "system",
64             #     f"This reminds you of these events from your past:\n{relevant_memory}\n\n",
65             # ),
66         ],
67     )
68 
69     # Add messages from the full message history until we reach the token limit
70     next_message_to_add_index = len(agent.history) - 1
71     insertion_index = len(message_sequence)
72     # Count the currently used tokens
73     current_tokens_used = message_sequence.token_length
74 
75     # while current_tokens_used > 2500:
76     #     # remove memories until we are under 2500 tokens
77     #     relevant_memory = relevant_memory[:-1]
78     #     (
79     #         next_message_to_add_index,
80     #         current_tokens_used,
81     #         insertion_index,
82     #         current_context,
83     #     ) = generate_context(
84     #         prompt, relevant_memory, agent.history, model
85     #     )
86 
87     # Account for user input (appended later)
88     user_input_msg = Message("user", user_input)
89     current_tokens_used += count_message_tokens([user_input_msg], model)
90 
91     current_tokens_used += 500  # Reserve space for new_summary_message
92 
93     # Add Messages until the token limit is reached or there are no more messages to add.
94     for cycle in reversed(list(agent.history.per_cycle())):
95         messages_to_add = [msg for msg in cycle if msg is not None]
96         tokens_to_add = count_message_tokens(messages_to_add, model)
97         if current_tokens_used + tokens_to_add > send_token_limit:
98             break
99 
100         # Add the most recent message to the start of the chain,
101         #  after the system prompts.
102         message_sequence.insert(insertion_index, *messages_to_add)
103         current_tokens_used += tokens_to_add
104 
105     # Update & add summary of trimmed messages
106     if len(agent.history) > 0:
107         new_summary_message, trimmed_messages = agent.history.trim_messages(
108             current_message_chain=list(message_sequence),
109         )
110         tokens_to_add = count_message_tokens([new_summary_message], model)
111         message_sequence.insert(insertion_index, new_summary_message)
112         current_tokens_used += tokens_to_add - 500
113 
114         # FIXME: uncomment when memory is back in use
115         # memory_store = get_memory(cfg)
116         # for _, ai_msg, result_msg in agent.history.per_cycle(trimmed_messages):
117         #     memory_to_add = MemoryItem.from_ai_action(ai_msg, result_msg)
118         #     logger.debug(f"Storing the following memory:\n{memory_to_add.dump()}")
119         #     memory_store.add(memory_to_add)
120 
121     api_manager = ApiManager()
122     # inform the AI about its remaining budget (if it has one)
123     if api_manager.get_total_budget() > 0.0:
124         remaining_budget = api_manager.get_total_budget() - api_manager.get_total_cost()
125         if remaining_budget < 0:
126             remaining_budget = 0
127         budget_message = f"Your remaining API budget is ${remaining_budget:.3f}" + (
128             " BUDGET EXCEEDED! SHUT DOWN!\n\n"
129             if remaining_budget == 0
130             else " Budget very nearly exceeded! Shut down gracefully!\n\n"
131             if remaining_budget < 0.005
132             else " Budget nearly exceeded. Finish up.\n\n"
133             if remaining_budget < 0.01
134             else "\n\n"
135         )
136         logger.debug(budget_message)
137         message_sequence.add("system", budget_message)
138         current_tokens_used += count_message_tokens([message_sequence[-1]], model)
139 
140     # Append user input, the length of this is accounted for above
141     message_sequence.append(user_input_msg)
142 
143     plugin_count = len(cfg.plugins)
144     for i, plugin in enumerate(cfg.plugins):
145         if not plugin.can_handle_on_planning():
146             continue
147         plugin_response = plugin.on_planning(
148             agent.config.prompt_generator, message_sequence.raw()
149         )
150         if not plugin_response or plugin_response == "":
151             continue
152         tokens_to_add = count_message_tokens(
153             [Message("system", plugin_response)], model
154         )
155         if current_tokens_used + tokens_to_add > send_token_limit:
156             logger.debug(f"Plugin response too long, skipping: {plugin_response}")
157             logger.debug(f"Plugins remaining at stop: {plugin_count - i}")
158             break
159         message_sequence.add("system", plugin_response)
160 
161     # Calculate remaining tokens
162     tokens_remaining = token_limit - current_tokens_used
163     # assert tokens_remaining >= 0, "Tokens remaining is negative.
164     # This should never happen, please submit a bug report at
165     #  https://www.github.com/Torantulino/Auto-GPT"
166 
167     # Debug print the current context
168     logger.debug(f"Token limit: {token_limit}")
169     logger.debug(f"Send Token Count: {current_tokens_used}")
170     logger.debug(f"Tokens remaining for response: {tokens_remaining}")
171     logger.debug("------------ CONTEXT SENT TO AI ---------------")
172     for message in message_sequence:
173         # Skip printing the prompt
174         if message.role == "system" and message.content == system_prompt:
175             continue
176         logger.debug(f"{message.role.capitalize()}: {message.content}")
177         logger.debug("")
178     logger.debug("----------- END OF CONTEXT ----------------")
179     agent.log_cycle_handler.log_cycle(
180         agent.config.ai_name,
181         agent.created_at,
182         agent.cycle_count,
183         message_sequence.raw(),
184         CURRENT_CONTEXT_FILE_NAME,
185     )
186 
187     # TODO: use a model defined elsewhere, so that model can contain
188     # temperature and other settings we care about
189     assistant_reply = create_chat_completion(
190         prompt=message_sequence,
191         max_tokens=tokens_remaining,
192     )
193 
194     # Update full message history
195     agent.history.append(user_input_msg)
196     agent.history.add("assistant", assistant_reply, "ai_response")
197 
198     return assistant_reply</original>
<patched>20 def chat_with_ai(
21     agent: Agent,
22     system_prompt: str,
23     user_input: str,
24     token_limit: int,
25     model: str,
26 ):
27     """
28     Interact with the OpenAI API, sending the prompt, user input,
29         message history, and permanent memory.
30 
31     Args:
32         system_prompt (str): The prompt explaining the rules to the AI.
33         user_input (str): The input from the user.
34         token_limit (int): The maximum number of tokens allowed in the API call.
35         model (str): The model to use for the chat completion.
36 
37     Returns:
38     str: The AI's response.
39     """
40    