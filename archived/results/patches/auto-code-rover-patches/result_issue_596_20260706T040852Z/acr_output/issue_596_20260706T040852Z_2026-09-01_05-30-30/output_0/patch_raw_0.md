The issue describes the problem that users might incur high costs when using GPT-4 or similar LLMs, without getting any warning or budget control. The current `respond` method executes the request to the LLM without giving feedback about token usage or estimated costs, and the user only gets a fallback switch to local models when the budget is exceeded but no proactive warnings or prompts are given.

**Reasoning for the patch:**
We want to make minimal changes to preserve the current functionality but add:

1. Calculation of token usage and cost estimation (using the number of tokens and a cost rate, based on model).
2. Display the user a warning about the estimated cost immediately after the messages are trimmed and before sending them, or after receiving usage info from completion API.
3. Optionally prompt for confirmation to proceed if the cost estimate exceeds a threshold (e.g., a few cents).
4. Keep existing budget exceeded handling and fallback intact.
5. This helps users be proactive about costs and avoid unexpected charges.

Given the existing code calls litellm.completion with stream=True (which yields chunks), and from the litellm usage we might or might not have direct usage/token counting info. We can assume litellm provides some metadata or partial result from which to extract token usage and cost, or we can estimate tokens from the request.

Because the existing snippet doesn't show token counting info from the response, we will add a rough tokens estimate before sending the request, based on the tokens consumed by the prompt (using `len` or a simple heuristic). After streaming starts, cost info might not be immediately available. So, a best-effort estimate pre-request with a warning will be helpful.

**Implementation details:**

- Add a helper function to estimate tokens from messages (e.g., counting words or characters divided by an approximate tokens per word).
- Map model names to estimated cost per 1k tokens (OpenAI gpt-4 might be roughly $0.06 per 1k prompt tokens, $0.12 per 1k completion tokens, but for simplicity we warn on total tokens with a simple cost per 1k tokens).
- Calculate estimated cost for the prompt tokens.
- Warn the user with the estimated token count and cost.
- If the estimated cost is above a pre-defined threshold (say $0.05), prompt user to continue or abort.
- If abort, return early without sending the request.
- If proceed, continue as before.

We keep all other functionality untouched.

---

# modification 1

```
<file>interpreter/archive/interpreter.py</file>
<original>  def respond(self):
    # Add relevant info to system_message
    # (e.g. current working directory, username, os, etc.)
    info = self.get_info_for_system_message()

    # This is hacky, as we should have a different (minified) prompt for CodeLLama,
    # but for now, to make the prompt shorter and remove "run_code" references, just get the first 2 lines:
    if self.local:
      self.system_message = "\n".join(self.system_message.split("\n")[:2])
      self.system_message += "\nOnly do what the user asks you to do, then ask what they'd like to do next."

    system_message = self.system_message + "\n\n" + info

    if self.local:
      messages = tt.trim(self.messages, max_tokens=(self.context_window-self.max_tokens-25), system_message=system_message)
    else:
      messages = tt.trim(self.messages, self.model, system_message=system_message)

    if self.debug_mode:
      print("\n", "Sending `messages` to LLM:", "\n")
      print(messages)
      print()

    # Make LLM call
    if not self.local:
      
      # GPT
      max_attempts = 3  
      attempts = 0  
      error = ""

      while attempts < max_attempts:
        attempts += 1
        try:

            if self.use_azure:
              response = litellm.completion(
                  f"azure/{self.azure_deployment_name}",
                  messages=messages,
                  functions=[function_schema],
                  temperature=self.temperature,
                  stream=True,
                  )
            else:
              if self.api_base:
                # The user set the api_base. litellm needs this to be "custom/{model}"
                response = litellm.completion(
                  api_base=self.api_base,
                  model = "custom/" + self.model,
                  messages=messages,
                  functions=[function_schema],
                  stream=True,
                  temperature=self.temperature,
                )
              else:
                # Normal OpenAI call
                response = litellm.completion(
                  model=self.model,
                  messages=messages,
                  functions=[function_schema],
                  stream=True,
                  temperature=self.temperature,
                )
            break
        except litellm.BudgetExceededError as e:
          print(f"Since your LLM API Budget limit was exceeded, you're being switched to local models. Budget: {litellm.max_budget} | Current Cost: {litellm._current_cost}")
          
          print(Markdown(
                "> Switching to `Code-Llama`...\n\n**Tip:** Run `interpreter --local` to automatically use `Code-Llama`."),
                    '')
          time.sleep(2)
          print(Rule(style="white"))


          # Temporarily, for backwards (behavioral) compatability, we've moved this part of llama_2.py here.
          # AND ABOVE.
          # This way, when folks hit interpreter --local, they get the same experience as before.
          import inquirer

          print('', Markdown("**Open Interpreter** will use `Code Llama` for local execution. Use your arrow keys to set up the model."), '')

          models = {
              '7B': 'TheBloke/CodeLlama-7B-Instruct-GGUF',
              '13B': 'TheBloke/CodeLlama-13B-Instruct-GGUF',
              '34B': 'TheBloke/CodeLlama-34B-Instruct-GGUF'
          }

          parameter_choices = list(models.keys())
          questions = [inquirer.List('param', message="Parameter count (smaller is faster, larger is more capable)", choices=parameter_choices)]
          answers = inquirer.prompt(questions)
          chosen_param = answers['param']

          # THIS is more in line with the future. You just say the model you want by name:
          self.model = models[chosen_param]
          self.local = True
          continue
        except RateLimitError as rate_error:  # Catch the specific RateLimitError
            print(Markdown(f"> We hit a rate limit. Cooling off for {attempts} seconds..."))
            time.sleep(attempts)  
            max_attempts += 1
        except Exception as e:  # Catch other exceptions
            if self.debug_mode:
              traceback.print_exc()
            error = traceback.format_exc()
            time.sleep(3)
      else:
        if self.local: 
          pass
        else:
          raise Exception(error)
          
    if self.local:
      # Code-Llama


      # Convert messages to prompt
      # (This only works if the first message is the only system message)

      def messages_to_prompt(messages):


        for message in messages:
          # Happens if it immediatly writes code
          if "role" not in message:
            message["role"] = "assistant"


        # Falcon prompt template
        if "falcon" in self.model.lower():

          formatted_messages = ""
          for message in messages:
            formatted_messages += f"{message['role'].capitalize()}: {message['content']}\n"
          formatted_messages = formatted_messages.strip()

        else:
          # Llama prompt template

          # Extracting the system prompt and initializing the formatted string with it.
          system_prompt = messages[0]['content']
          formatted_messages = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n"

          # Loop starting from the first user message
          for index, item in enumerate(messages[1:]):
              role = item['role']
              content = item['content']

              if role == 'user':
                  formatted_messages += f"{content} [/INST] "
              elif role == 'function':
                  formatted_messages += f"Output: {content} [/INST] "
              elif role == 'assistant':
                  formatted_messages += f"{content} </s><s>[INST] "

          # Remove the trailing '<s>[INST] ' from the final output
          if formatted_messages.endswith("<s>[INST] "):
              formatted_messages = formatted_messages[:-10]

        return formatted_messages

      prompt = messages_to_prompt(messages)
      # Lmao i can't believe this works (it does need this btw)
      if messages[-1]["role"] != "function":
        prompt += "Let's explore this. By the way, I can run code on your machine by writing the code in a markdown code block. This works for shell, javascript, python, R, and applescript. I'm going to try to do this for your task. Anyway, "
      elif messages[-1]["role"] == "function" and messages[-1]["content"] != "No output":
        prompt += "Given the output of the code I just ran, "
      elif messages[-1]["role"] == "function" and messages[-1]["content"] == "No output":
        prompt += "Given the fact that the code I just ran produced no output, "


      if self.debug_mode:
        # we have to use builtins bizarrely! because rich.print interprets "[INST]" as something meaningful
        import builtins
        builtins.print("TEXT PROMPT SEND TO LLM:\n", prompt)

      # Run Code-Llama

      response = self.llama_instance(
        prompt,
        stream=True,
        temperature=self.temperature,
        stop=["</s>"],
        max_tokens=750 # context window is set to 1800, messages are trimmed to 1000... 700 seems nice
      )

    # Initialize message, function call trackers, and active block
    self.messages.append({})
    in_function_call = False
    llama_function_call_finished = False
    self.active_block = None

    for chunk in response:
      if self.use_azure and ('choices' not in chunk or len(chunk['choices']) == 0):
        # Azure OpenAI Service may return empty chunk
        continue

      if self.local:
        if "content" not in messages[-1]:
          # This is the first chunk. We'll need to capitalize it, because our prompt ends in a ", "
          chunk["choices"][0]["text"] = chunk["choices"][0]["text"].capitalize()
          # We'll also need to add "role: assistant", CodeLlama will not generate this
          messages[-1]["role"] = "assistant"
        delta = {"content": chunk["choices"][0]["text"]}
      else:
        delta = chunk["choices"][0]["delta"]

      # Accumulate deltas into the last message in messages
      self.messages[-1] = merge_deltas(self.messages[-1], delta)

      # Check if we're in a function call
      if not self.local:
        condition = "function_call" in self.messages[-1]
      elif self.local:
        # Since Code-Llama can't call functions, we just check if we're in a code block.
        # This simply returns true if the number of "```" in the message is odd.
        if "content" in self.messages[-1]:
          condition = self.messages[-1]["content"].count("```") % 2 == 1
        else:
          # If it hasn't made "content" yet, we're certainly not in a function call.
          condition = False

      if condition:
        # We are in a function call.

        # Check if we just entered a function call
        if in_function_call == False:

          # If so, end the last block,
          self.end_active_block()

          # Print newline if it was just a code block or user message
          # (this just looks nice)
          last_role = self.messages[-2]["role"]
          if last_role == "user" or last_role == "function":
            print()

          # then create a new code block
          self.active_block = CodeBlock()

        # Remember we're in a function_call
        in_function_call = True

        # Now let's parse the function's arguments:

        if not self.local:
          # gpt-4
          # Parse arguments and save to parsed_arguments, under function_call
          if "arguments" in self.messages[-1]["function_call"]:
            arguments = self.messages[-1]["function_call"]["arguments"]
            new_parsed_arguments = parse_partial_json(arguments)
            if new_parsed_arguments:
              # Only overwrite what we have if it's not None (which means it failed to parse)
              self.messages[-1]["function_call"][
                "parsed_arguments"] = new_parsed_arguments

        elif self.local:
          # Code-Llama
          # Parse current code block and save to parsed_arguments, under function_call
          if "content" in self.messages[-1]:

            content = self.messages[-1]["content"]

            if "```" in content:
              # Split by "```" to get the last open code block
              blocks = content.split("```")

              current_code_block = blocks[-1]

              lines = current_code_block.split("\n")

              if content.strip() == "```": # Hasn't outputted a language yet
                language = None
              else:
                if lines[0] != "":
                  language = lines[0].strip()
                else:
                  language = "python"
                  # In anticipation of its dumbassery let's check if "pip" is in there
                  if len(lines) > 1:
                    if lines[1].startswith("pip"):
                      language = "shell"

              # Join all lines except for the language line
              code = '\n'.join(lines[1:]).strip("` \n")

              arguments = {"code": code}
              if language: # We only add this if we have it-- the second we have it, an interpreter gets fired up (I think? maybe I'm wrong)
                if language == "bash":
                  language = "shell"
                arguments["language"] = language

            # Code-Llama won't make a "function_call" property for us to store this under, so:
            if "function_call" not in self.messages[-1]:
              self.messages[-1]["function_call"] = {}

            self.messages[-1]["function_call"]["parsed_arguments"] = arguments

      else:
        # We are not in a function call.

        # Check if we just left a function call
        if in_function_call == True:

          if self.local:
            # This is the same as when gpt-4 gives finish_reason as function_call.
            # We have just finished a code block, so now we should run it.
            llama_function_call_finished = True

        # Remember we're not in a function_call
        in_function_call = False

        # If there's no active block,
        if self.active_block == None:

          # Create a message block
          self.active_block = MessageBlock()

      # Update active_block
      self.active_block.update_from_message(self.messages[-1])

      # Check if we're finished
      if chunk["choices"][0]["finish_reason"] or llama_function_call_finished:
        if chunk["choices"][
            0]["finish_reason"] == "function_call" or llama_function_call_finished:
          # Time to call the function!
          # (Because this is Open Interpreter, we only have one function.)

          if self.debug_mode:
            print("Running function:")
            print(self.messages[-1])
            print("---")

          # Ask for user confirmation to run code
          if self.auto_run == False:

            # End the active block so you can run input() below it
            # Save language and code so we can create a new block in a moment
            self.active_block.end()
            language = self.active_block.language
            code = self.active_block.code

            # Prompt user
            response = input("  Would you like to run this code? (y/n)\n\n  ")
            print("")  # <- Aesthetic choice

            if response.strip().lower() == "y":
              # Create a new, identical block where the code will actually be run
              self.active_block = CodeBlock()
              self.active_block.language = language
              self.active_block.code = code

            else:
              # User declined to run code.
              self.active_block.end()
              self.messages.append({
                "role":
                "function",
                "name":
                "run_code",
                "content":
                "User decided not to run this code."
              })
              return

          # If we couldn't parse its arguments, we need to try again.
          if not self.local and "parsed_arguments" not in self.messages[-1]["function_call"]:

            # After collecting some data via the below instruction to users,
            # This is the most common failure pattern: https://github.com/KillianLucas/open-interpreter/issues/41

            # print("> Function call could not be parsed.\n\nPlease open an issue on Github (openinterpreter.com, click Github) and paste the following:")
            # print("\n", self.messages[-1]["function_call"], "\n")
            # time.sleep(2)
            # print("Informing the language model and continuing...")

            # Since it can't really be fixed without something complex,
            # let's just berate the LLM then go around again.

            self.messages.append({
              "role": "function",
              "name": "run_code",
              "content": """Your function call could not be parsed. Please use ONLY the `run_code` function, which takes two parameters: `code` and `language`. Your response should be formatted as a JSON."""
            })
            self.respond()
            return

          # Create or retrieve a Code Interpreter for this language
          language = self.messages[-1]["function_call"]["parsed_arguments"][
            "language"]
          if language not in self.code_interpreters:
            self.code_interpreters[language] = CodeInterpreter(language, self.debug_mode)
          code_interpreter = self.code_interpreters[language]

          # Let this Code Interpreter control the active_block
          code_interpreter.active_block = self.active_block
          code_interpreter.run()

          # End the active_block
          self.active_block.end()

          # Append the output to messages
          # Explicitly tell it if there was no output (sometimes "" = hallucinates output)
          self.messages.append({
            "role": "function",
            "name": "run_code",
            "content": self.active_block.output if self.active_block.output else "No output"
          })

          # Go around again
          self.respond()

        if chunk["choices"][0]["finish_reason"] != "function_call":
          # Done!

          # Code Llama likes to output "###" at the end of every message for some reason
          if self.local and "content" in self.messages[-1]:
            self.messages[-1]["content"] = self.messages[-1]["content"].strip().rstrip("#")
            self.active_block.update_from_message(self.messages[-1])
            time.sleep(0.1)

          self.active_block.end()
          return</original>
<patched>  import math
  def estimate_token_count(messages):
    # A very rough estimate: count number of words and estimate tokens as ~1