Reasoning:

The issue requests warning the user about token consumption or costs when using OpenAI LLMs, since the billing limits don't work well and users can overspend easily.

To address this:

1. In `interpreter/llm/setup_openai_coding_llm.py`:
   - After consuming the stream of response chunks, we can access token usage or cost info if available.
   - `litellm.completion` returns a generator yielding chunks of completions but might not provide usage info directly in chunks. However, `litellm` maintains `litellm._current_cost` and `litellm._current_tokens` internally which can be used for the current session's cost and tokens.
   - We can yield a special "usage" message after the streaming ends, giving token and cost info.
   - Additionally, if a max budget is set, we can proactively check and warn user when cost approaches the max budget (e.g., at 80% usage).

2. In `interpreter/core/respond.py`:
   - Currently, a budget exceed exception triggers a markdown warning and exits.
   - We can add a periodic cost/token usage warning in the normal flow, after each completion or message stream finishes.
   - Because `respond()` gets the streaming chunks from `interpreter._llm()`, which is set to the function from the LLM setup, and the new "usage" messages can be yielded from the LLM generator after response is finished, we can detect those and display info accordingly.
   - Alternatively, since `litellm._current_cost` is a global state, we can display a cost/token usage update after completing each response from the model inside `respond()`.

Overall, minimal changes are made to the coding LLM function to yield usage info at the end, and in respond() to detect and display these warnings, helping users avoid surprises.

---

Patch:

# modification 1
```
<file>interpreter/llm/setup_openai_coding_llm.py</file>
<original>31 def setup_openai_coding_llm(interpreter):
32     """
33     Takes an Interpreter (which includes a ton of LLM settings),
34     returns a OI Coding LLM (a generator that takes OI messages and streams deltas with `message`, `language`, and `code`).
35     """
36 
37     def coding_llm(messages):
38         
39         # Convert messages
40         messages = convert_to_openai_messages(messages)
41 
42         # Add OpenAI's recommended function message
43         messages[0]["content"] += "\n\nOnly use the function you have been provided with."
44 
45         # Seperate out the system_message from messages
46         # (We expect the first message to always be a system_message)
47         system_message = messages[0]["content"]
48         messages = messages[1:]
49 
50         # Trim messages, preserving the system_message
51         try:
52             messages = tt.trim(messages=messages, system_message=system_message, model=interpreter.model)
53         except:
54             if interpreter.context_window:
55                 messages = tt.trim(messages=messages, system_message=system_message, max_tokens=interpreter.context_window)
56             else:
57                 display_markdown_message("""
58                 **We were unable to determine the context window of this model.** Defaulting to 3000.
59                 If your model can handle more, run `interpreter --context_window {token limit}` or `interpreter.context_window = {token limit}`.
60                 """)
61                 messages = tt.trim(messages=messages, system_message=system_message, max_tokens=3000)
62 
63         if interpreter.debug_mode:
64             print("Sending this to the OpenAI LLM:", messages)
65 
66         # Create LiteLLM generator
67         params = {
68             'model': interpreter.model,
69             'messages': messages,
70             'stream': True,
71             'functions': [function_schema]
72         }
73 
74         # Optional inputs
75         if interpreter.api_base:
76             params["api_base"] = interpreter.api_base
77         if interpreter.api_key:
78             params["api_key"] = interpreter.api_key
79         if interpreter.max_tokens:
80             params["max_tokens"] = interpreter.max_tokens
81         if interpreter.temperature:
82             params["temperature"] = interpreter.temperature
83         
84         # These are set directly on LiteLLM
85         if interpreter.max_budget:
86             litellm.max_budget = interpreter.max_budget
87         if interpreter.debug_mode:
88             litellm.set_verbose = True
89 
90         # Report what we're sending to LiteLLM
91         if interpreter.debug_mode:
92             print("Sending this to LiteLLM:", params)
93 
94         response = litellm.completion(**params)
95 
96         accumulated_deltas = {}
97         language = None
98         code = ""
99 
100         for chunk in response:
101 
102             if ('choices' not in chunk or len(chunk['choices']) == 0):
103                 # This happens sometimes
104                 continue
105 
106             delta = chunk["choices"][0]["delta"]
107 
108             # Accumulate deltas
109             accumulated_deltas = merge_deltas(accumulated_deltas, delta)
110 
111             if "content" in delta and delta["content"]:
112                 yield {"message": delta["content"]}
113 
114             if ("function_call" in accumulated_deltas 
115                 and "arguments" in accumulated_deltas["function_call"]):
116 
117                 arguments = accumulated_deltas["function_call"]["arguments"]
118                 arguments = parse_partial_json(arguments)
119 
120                 if arguments:
121 
122                     if (language is None
123                         and "language" in arguments
124                         and "code" in arguments # <- This ensures we're *finished* typing language, as opposed to partially done
125                         and arguments["language"]):
126                         language = arguments["language"]
127                         yield {"language": language}
128                     
129                     if language is not None and "code" in arguments:
130                         # Calculate the delta (new characters only)
131                         code_delta = arguments["code"][len(code):]
132                         # Update the code
133                         code = arguments["code"]
134                         # Yield the delta
135                         if code_delta:
136                           yield {"code": code_delta}
137             
138     return coding_llm</original>
<patched>31 def setup_openai_coding_llm(interpreter):
32     """
33     Takes an Interpreter (which includes a ton of LLM settings),
34     returns a OI Coding LLM (a generator that takes OI messages and streams deltas with `message`, `language`, and `code`).
35     """
36 
37     def coding_llm(messages):
38         
39         # Convert messages
40         messages = convert_to_openai_messages(messages)
41 
42         # Add OpenAI's recommended function message
43         messages[0]["content"] += "\n\nOnly use the function you have been provided with."
44 
45         # Seperate out the system_message from messages
46         # (We expect the first message to always be a system_message)
47         system_message = messages[0]["content"]
48         messages = messages[1:]
49 
50         # Trim messages, preserving the system_message
51         try:
52             messages = tt.trim(messages=messages, system_message=system_message, model=interpreter.model)
53         except:
54             if interpreter.context_window:
55                 messages = tt.trim(messages=messages, system_message=system_message, max_tokens=interpreter.context_window)
56             else:
57                 display_markdown_message("""
58                 **We were unable to determine the context window of this model.** Defaulting to 3000.
59                 If your model can handle more, run `interpreter --context_window {token limit}` or `interpreter.context_window = {token limit}`.
60                 """)
61                 messages = tt.trim(messages=messages, system_message=system_message, max_tokens=3000)
62 
63         if interpreter.debug_mode:
64             print("Sending this to the OpenAI LLM:", messages)
65 
66         # Create LiteLLM generator
67         params = {
68             'model': interpreter.model,
69             'messages': messages,
70             'stream': True,
71             'functions': [function_schema]
72         }
73 
74         # Optional inputs
75         if interpreter.api_base:
76             params["api_base"] = interpreter.api_base
77         if interpreter.api_key:
78             params["api_key"] = interpreter.api_key
79         if interpreter.max_tokens:
80             params["max_tokens"] = interpreter.max_tokens
81         if interpreter.temperature:
82             params["temperature"] = interpreter.temperature
83         
84         # These are set directly on LiteLLM
85         if interpreter.max_budget:
86             litellm.max_budget = interpreter.max_budget
87         if interpreter.debug_mode:
88             litellm.set_verbose = True
89 
90         # Report what we're sending to LiteLLM
91         if interpreter.debug_mode:
92             print("Sending this to LiteLLM:", params)
93 
94         response = litellm.completion(**params)
95 
96         accumulated_deltas = {}
97         language = None
98         code = ""
99 
100         for chunk in response:
101 
102             if ('choices' not in chunk or len(chunk['choices']) == 0):
103                 # This happens sometimes
104                 continue
105 
106             delta = chunk["choices"][0]["delta"]
107 
108             # Accumulate deltas
109             accumulated_deltas = merge_deltas(accumulated_deltas, delta)
110 
111             if "content" in delta and delta["content"]:
112                 yield {"message": delta["content"]}
113 
114             if ("function_call" in accumulated_deltas 
115                 and "arguments" in accumulated_deltas["function_call"]):
116 
117                 arguments = accumulated_deltas["function_call"]["arguments"]
118                 arguments = parse_partial_json(arguments)
119 
120                 if arguments:
121 
122                     if (language is None
123                         and "language" in arguments
124                         and "code" in arguments # <- This ensures we're *finished* typing language, as opposed to partially done
125                         and arguments["language"]):
126                         language = arguments["language"]
127                         yield {"language": language}
128                     
129                     if language is not None and "code" in arguments:
130                         # Calculate the delta (new characters only)
131                         code_delta = arguments["code"][len(code):]
132                         # Update the code
133                         code = arguments["code"]
134                         # Yield the delta
135                         if code_delta:
136                           yield {"code": code_delta}
137 
138         # After the generator finishes, yield usage info if available
139         try:
140             # Try to get tokens and cost summary from litellm internal state
141             current_tokens = getattr(litellm, "_current_tokens", None)
142             current_cost = getattr(litellm, "_current_cost", None)
143             max_budget = getattr(litellm, "max_budget", None)
144 
145             if current_tokens is not None and current_cost is not None:
146                 usage_message = f"Current total tokens used: {current_tokens}, cost so far: ${current_cost:.5f}"
147 
148                 if max_budget is not None:
149                     # Warn if we're near (>= 80%) or exceeded budget
150                     if current_cost >= max_budget:
151                         usage_message += " - WARNING: Max budget exceeded!"
152                     elif current_cost >= 0.8 * max_budget:
153                         usage_message += " - WARNING: Approaching max budget."
154 
155                 yield {"usage_warning": usage_message}
156         except Exception:
157             # Ignore any errors here, don't affect the main generator response
158             pass
159     
160     return coding_llm
</patched>
```

# modification 2
```
<file>interpreter/core/respond.py</file>
<original>10 def respond(interpreter):
11     """
12     Yields tokens, but also adds them to interpreter.messages. TBH probably would be good to seperate those two responsibilities someday soon
13     Responds until it decides not to run any more code or say anything else.
14     """
15 
16     while True:
17 
18         ### PREPARE MESSAGES ###
19 
20         system_message = interpreter.system_message
21         
22         # Open Procedures is an open-source database of tiny, up-to-date coding tutorials.
23         # We can query it semantically and append relevant tutorials/procedures to our system message
24         get_relevant_procedures(interpreter.messages[-2:])
25         if not interpreter.local:
26             try:
27                 system_message += "\n\n" + get_relevant_procedures(interpreter.messages[-2:])
28             except:
29                 # This can fail for odd SLL reasons. It's not necessary, so we can continue
30                 pass
31         
32         # Add user info to system_message, like OS, CWD, etc
33         system_message += "\n\n" + get_user_info_string()
34 
35         # Create message object
36         system_message = {"role": "system", "message": system_message}
37 
38         # Create the version of messages that we'll send to the LLM
39         messages_for_llm = interpreter.messages.copy()
40         messages_for_llm = [system_message] + messages_for_llm
41 
42         # It's best to explicitly tell these LLMs when they don't get an output
43         for message in messages_for_llm:
44             if "output" in message and message["output"] == "":
45                 message["output"] = "No output"
46 
47 
48         ### RUN THE LLM ###
49 
50         # Add a new message from the assistant to interpreter's "messages" attribute
51         # (This doesn't go to the LLM. We fill this up w/ the LLM's response)
52         interpreter.messages.append({"role": "assistant"})
53 
54         # Start putting chunks into the new message
55         # + yielding chunks to the user
56         try:
57             for chunk in interpreter._llm(messages_for_llm):
58 
59                 # Add chunk to the last message
60                 interpreter.messages[-1] = merge_deltas(interpreter.messages[-1], chunk)
61 
62                 # This is a coding llm
63                 # It will yield dict with either a message, language, or code (or language AND code)
64                 yield chunk
65         except litellm.exceptions.BudgetExceededError:
66             display_markdown_message(f"""> Max budget exceeded
67 
68                 **Session spend:** ${litellm._current_cost}
69                 **Max budget:** ${interpreter.max_budget}
70 
71                 Press CTRL-C then run `interpreter --max_budget [higher USD amount]` to proceed.
72             """)
73             break
74         # Provide extra information on how to change API keys, if we encounter that error
75         # (Many people writing GitHub issues were struggling with this)
76         except Exception as e:
77             if 'auth' in str(e).lower() or 'api key' in str(e).lower():
78                 output = traceback.format_exc()
79                 raise Exception(f"{output}\n\nThere might be an issue with your API key(s).\n\nTo reset your API key (we'll use OPENAI_API_KEY for this example, but you may need to reset your ANTHROPIC_API_KEY, HUGGINGFACE_API_KEY, etc):\n        Mac/Linux: 'export OPENAI_API_KEY=your-key-here',\n        Windows: 'setx OPENAI_API_KEY your-key-here' then restart terminal.\n\n")
80             else:
81                 raise
82         
83         
84         
85         ### RUN CODE (if it's there) ###
86 
87         if "code" in interpreter.messages[-1]:
88             
89             if interpreter.debug_mode:
90                 print("Running code:", interpreter.messages[-1])
91 
92             try:
93                 # What code do you want to run?
94                 code = interpreter.messages[-1]["code"]
95 
96                 # Fix a common error where the LLM thinks it's in a Jupyter notebook
97                 if interpreter.messages[-1]["language"] == "python" and code.startswith("!"):
98                     code = code[1:]
99                     interpreter.messages[-1]["code"] = code
100                     interpreter.messages[-1]["language"] = "shell"
101 
102                 # Get a code interpreter to run it
103                 language = interpreter.messages[-1]["language"]
104                 if language not in interpreter._code_interpreters:
105                     interpreter._code_interpreters[language] = create_code_interpreter(language)
106                 code_interpreter = interpreter._code_interpreters[language]
107 
108                 # Yield a message, such that the user can stop code execution if they want to
109                 try:
110                     yield {"executing": {"code": code, "language": language}}
111                 except GeneratorExit:
112                     # The user might exit here.
113                     # We need to tell python what we (the generator) should do if they exit
114                     break
115 
116                 # Yield each line, also append it to last messages' output
117                 interpreter.messages[-1]["output"] = ""
118                 for line in code_interpreter.run(code):
119                     yield line
120                     if "output" in line:
121                         output = interpreter.messages[-1]["output"]
122                         output += "\n" + line["output"]
123 
124                         # Truncate output
125                         output = truncate_output(output, interpreter.max_output)
126 
127                         interpreter.messages[-1]["output"] = output.strip()
128 
129             except:
130                 output = traceback.format_exc()
131                 yield {"output": output.strip()}
132                 interpreter.messages[-1]["output"] = output.strip()
133 
134             yield {"end_of_execution": True}
135 
136         else:
137             # Doesn't want to run code. We're done
138             break
139 
140     return</original>
<patched>10 def respond(interpreter):
11     """
12     Yields tokens, but also adds them to interpreter.messages. TBH probably would be good to seperate those two responsibilities someday soon
13     Responds until it decides not to run any more code or say anything else.
14     """
15 
16     while True:
17 
18         ### PREPARE MESSAGES ###
19 
20         system_message = interpreter.system_message
21         
22         # Open Procedures is an open-source database of tiny, up-to-date coding tutorials.
23         # We can query it semantically and append relevant tutorials/procedures to our system message
24         get_relevant_procedures(interpreter.messages[-2:])
25         if not interpreter.local:
26             try:
27                 system_message += "\n\n" + get_relevant_procedures(interpreter.messages[-2:])
28             except:
29                 # This can fail for odd SLL reasons. It's not necessary, so we can continue
30                 pass
31         
