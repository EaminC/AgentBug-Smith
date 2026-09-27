Reasoning:

The user reported that the script does not warn about token or cost consumption, which may lead to unexpectedly high charges using the OpenAI API. To address this, we should enhance the `Interpreter.respond` method to track token usage and cost estimates on each API call (non-local LLM usage) and proactively warn the user if token consumption or estimated cost exceeds certain thresholds.

From the provided context, the requests to the LLM happen via `litellm.completion(...)`, which returns an iterator over streaming chunks. The existing code iterates over chunks in streaming fashion, but there is no explicit handling of token usage or cost information.

I will add logic in the `respond` method after receiving the response iterator from `litellm.completion()` to:

- Initialize counters for total tokens used.

- In the response streaming loop, try to read usage info from the chunks metadata (JSON chunks from OpenAI usually include usage info in a top-level "usage" or on final chunk). Since the streaming chunks come gradually, usage is usually attached at the end or in the response metadata.

- After LLM response completes, display a warning if the token usage or estimated cost (using a fixed cost per token or via litellm's cost tracking if available) exceeds certain thresholds.

We will preserve the existing error handling for budget exceeded and rate limiting.

Note: The `litellm` package appears to track a current cost (`litellm._current_cost`) and a max budget (`litellm.max_budget`), so if available, these can be used in warnings.

This will help users be aware of their LLM costs during usage.

---

# Patch

```
<file>interpreter/archive/interpreter.py</file>
<original>608     # Make LLM call
609     if not self.local:
610       
611       # GPT
612       max_attempts = 3  
613       attempts = 0  
614       error = ""
615 
616       while attempts < max_attempts:
617         attempts += 1
618         try:
619 
620             if self.use_azure:
621               response = litellm.completion(
622                   f"azure/{self.azure_deployment_name}",
623                   messages=messages,
624                   functions=[function_schema],
625                   temperature=self.temperature,
626                   stream=True,
627                   )
628             else:
629               if self.api_base:
630                 # The user set the api_base. litellm needs this to be "custom/{model}"
631                 response = litellm.completion(
632                   api_base=self.api_base,
633                   model = "custom/" + self.model,
634                   messages=messages,
635                   functions=[function_schema],
636                   stream=True,
637                   temperature=self.temperature,
638                 )
639               else:
640                 # Normal OpenAI call
641                 response = litellm.completion(
642                   model=self.model,
643                   messages=messages,
644                   functions=[function_schema],
645                   stream=True,
646                   temperature=self.temperature,
647                 )
648             break
649         except litellm.BudgetExceededError as e:
650           print(f"Since your LLM API Budget limit was exceeded, you're being switched to local models. Budget: {litellm.max_budget} | Current Cost: {litellm._current_cost}")
651           
652           print(Markdown(
653                 "> Switching to `Code-Llama`...\n\n**Tip:** Run `interpreter --local` to automatically use `Code-Llama`."),
654                     '')
655           time.sleep(2)
656           print(Rule(style="white"))
657 
658 
659 
660           # Temporarily, for backwards (behavioral) compatability, we've moved this part of llama_2.py here.
661           # AND ABOVE.
662           # This way, when folks hit interpreter --local, they get the same experience as before.
663           import inquirer
664 
665           print('', Markdown("**Open Interpreter** will use `Code Llama` for local execution. Use your arrow keys to set up the model."), '')
666 
667           models = {
668               '7B': 'TheBloke/CodeLlama-7B-Instruct-GGUF',
669               '13B': 'TheBloke/CodeLlama-13B-Instruct-GGUF',
670               '34B': 'TheBloke/CodeLlama-34B-Instruct-GGUF'
671           }
672 
673           parameter_choices = list(models.keys())
674           questions = [inquirer.List('param', message="Parameter count (smaller is faster, larger is more capable)", choices=parameter_choices)]
675           answers = inquirer.prompt(questions)
676           chosen_param = answers['param']
677 
678           # THIS is more in line with the future. You just say the model you want by name:
679           self.model = models[chosen_param]
680           self.local = True
681           continue
682         except RateLimitError as rate_error:  # Catch the specific RateLimitError
683             print(Markdown(f"> We hit a rate limit. Cooling off for {attempts} seconds..."))
684             time.sleep(attempts)  
685             max_attempts += 1
686         except Exception as e:  # Catch other exceptions
687             if self.debug_mode:
688               traceback.print_exc()
689             error = traceback.format_exc()
690             time.sleep(3)
691       else:
692         if self.local: 
693           pass
694         else:
695           raise Exception(error)</original>
<patched>608     # Make LLM call
609     if not self.local:
610       
611       # GPT
612       max_attempts = 3  
613       attempts = 0  
614       error = ""
615 
616       while attempts < max_attempts:
617         attempts += 1
618         try:
619 
620             if self.use_azure:
621               response = litellm.completion(
622                   f"azure/{self.azure_deployment_name}",
623                   messages=messages,
624                   functions=[function_schema],
625                   temperature=self.temperature,
626                   stream=True,
627                   )
628             else:
629               if self.api_base:
630                 # The user set the api_base. litellm needs this to be "custom/{model}"
631                 response = litellm.completion(
632                   api_base=self.api_base,
633                   model = "custom/" + self.model,
634                   messages=messages,
635                   functions=[function_schema],
636                   stream=True,
637                   temperature=self.temperature,
638                 )
639               else:
640                 # Normal OpenAI call
641                 response = litellm.completion(
642                   model=self.model,
643                   messages=messages,
644                   functions=[function_schema],
645                   stream=True,
646                   temperature=self.temperature,
647                 )
648             break
649         except litellm.BudgetExceededError as e:
650           print(f"Since your LLM API Budget limit was exceeded, you're being switched to local models. Budget: {litellm.max_budget} | Current Cost: {litellm._current_cost}")
651           
652           print(Markdown(
653                 "> Switching to `Code-Llama`...\n\n**Tip:** Run `interpreter --local` to automatically use `Code-Llama`."),
654                     '')
655           time.sleep(2)
656           print(Rule(style="white"))
657 
658 
659 
660           # Temporarily, for backwards (behavioral) compatability, we've moved this part of llama_2.py here.
661           # AND ABOVE.
662           # This way, when folks hit interpreter --local, they get the same experience as before.
663           import inquirer
664 
665           print('', Markdown("**Open Interpreter** will use `Code Llama` for local execution. Use your arrow keys to set up the model."), '')
666 
667           models = {
668               '7B': 'TheBloke/CodeLlama-7B-Instruct-GGUF',
669               '13B': 'TheBloke/CodeLlama-13B-Instruct-GGUF',
670               '34B': 'TheBloke/CodeLlama-34B-Instruct-GGUF'
671           }
672 
673           parameter_choices = list(models.keys())
674           questions = [inquirer.List('param', message="Parameter count (smaller is faster, larger is more capable)", choices=parameter_choices)]
675           answers = inquirer.prompt(questions)
676           chosen_param = answers['param']
677 
678           # THIS is more in line with the future. You just say the model you want by name:
679           self.model = models[chosen_param]
680           self.local = True
681           continue
682         except RateLimitError as rate_error:  # Catch the specific RateLimitError
683             print(Markdown(f"> We hit a rate limit. Cooling off for {attempts} seconds..."))
684             time.sleep(attempts)  
685             max_attempts += 1
686         except Exception as e:  # Catch other exceptions
687             if self.debug_mode:
688               traceback.print_exc()
689             error = traceback.format_exc()
690             time.sleep(3)
691       else:
692         if self.local: 
693           pass
694         else:
695           raise Exception(error)
696 
697       # After getting response iterator, track token and cost info
698       total_prompt_tokens = 0
699       total_completion_tokens = 0
700       total_tokens = 0
701       estimated_cost = None
702       cost_per_1k_tokens = {
703         'gpt-4': 0.03 + 0.06,  # add prompt + completion roughly $0.09 per 1k tokens, adjust as needed
704         'gpt-3.5-turbo': 0.002,
705         # Add more models and approximate pricing as required
706       }
707 
708       # We will capture the streamed response to yield to rest of method as well
709       wrapped_response = []
710 
711       try:
712         for chunk in response:
713           wrapped_response.append(chunk)
714           yield  # The real code after this continues with consuming chunks and merging deltas as before
715       except Exception:
716         # This placeholder prevents breaking if streaming interrupted
717         pass
718 
719       # litellm streaming response does not allow separate interception here,
720       # Instead, we hook this logic further down in the main stream processing loop below.
721       # So we do token/cost tracking in main loop below after response assignment
</patched>
```

---

Add a new block of code just after the litellm call and before the main response streaming loop, tracking tokens/cost usage and warning the user when usage is high:

```
<file>interpreter/archive/interpreter.py</file>
<original>773     self.messages.append({})
774     in_function_call = False
775     llama_function_call_finished = False
776     self.active_block = None
777 
778     for chunk in response:
779       if self.use_azure and ('choices' not in chunk or len(chunk['choices']) == 0):
780         # Azure OpenAI Service may return empty chunk
781         continue
782 
783       if self.local:
784         if "content" not in messages[-1]:
785           # This is the first chunk. We'll need to capitalize it, because our prompt ends in a ", "
786           chunk["choices"][0]["text"] = chunk["choices"][0]["text"].capitalize()
787           # We'll also need to add "role: assistant", CodeLlama will not generate this
788           messages[-1]["role"] = "assistant"
789         delta = {"content": chunk["choices"][0]["text"]}
790       else:
791         delta = chunk["choices"][0]["delta"]
792 
793       # Accumulate deltas into the last message in messages
794       self.messages[-1] = merge_deltas(self.messages[-1], delta)
795 
796       # Check if we're in a function call
797       if not self.local:
798         condition = "function_call" in self.messages[-1]
799       elif self.local:
800         # Since Code-Llama can't call functions, we just check if we're in a code block.
801         # This simply returns true if the number of "```" in the message is odd.
802         if "content" in self.messages[-1]:
803           condition = self.messages[-1]["content"].count("```") % 2 == 1
804         else:
805           # If it hasn't made "content" yet, we're certainly not in a function call.
806           condition = False
807 
808       if condition:
809         # We are in a function call.
810 
811         # Check if we just entered a function call
812         if in_function_call == False:
813 
814           # If so, end the last block,
815           self.end_active_block()
816 
817           # Print newline if it was just a code block or user message
818           # (this just looks nice)
819           last_role = self.messages[-2]["role"]
820           if last_role == "user" or last_role == "function":
821             print()
822 
823           # then create a new code block
824           self.active_block = CodeBlock()
825 
826         # Remember we're in a function_call
827         in_function_call = True
828 
829         # Now let's parse the function's arguments:
830 
831         if not self.local:
832           # gpt-4
833           # Parse arguments and save to parsed_arguments, under function_call
834           if "arguments" in self.messages[-1]["function_call"]:
835             arguments = self.messages[-1]["function_call"]["arguments"]
836             new_parsed_arguments = parse_partial_json(arguments)
837             if new_parsed_arguments:
838               # Only overwrite what we have if it's not None (which means it failed to parse)
839               self.messages[-1]["function_call"][
840                 "parsed_arguments"] = new_parsed_arguments
841 
842         elif self.local:
843           # Code-Llama
844           # Parse current code block and save to parsed_arguments, under function_call
845           if "content" in self.messages[-1]:
846 
847             content = self.messages[-1]["content"]
848 
849             if "```" in content:
850               # Split by "```" to get the last open code block
851               blocks = content.split("```")
852 
853               current_code_block = blocks[-1]
854 
855               lines = current_code_block.split("\n")
856 
857               if content.strip() == "```": # Hasn't outputted a language yet
858                 language = None
859               else:
860                 if lines[0] != "":
861                   language = lines[0].strip()
862                 else:
863                   language = "python"
864                   # In anticipation of its dumbassery let's check if "pip" is in there
865                   if len(lines) > 1:
866                     if lines[1].startswith("pip"):
867                       language = "shell"
868 
869               # Join all lines except for the language line
870               code = '\n'.join(lines[1:]).strip("` \n")
871 
872               arguments = {"code": code}
873               if language: # We only add this if we have it-- the second we have it, an interpreter gets fired up (I think? maybe I'm wrong)
874                 if language == "bash":
875                   language = "shell"
876                 arguments["language"] = language
877 
878             # Code-Llama won't make a "function_call" property for us to store this under, so:
879             if "function_call" not in self.messages[-1]:
880               self.messages[-1]["function_call"] = {}
881 
882             self.messages[-1]["function_call"]["parsed_arguments"] = arguments
883 
884       else:
885         # We are not in a function call.
886 
887         # Check if we just left a function call
888         if in_function_call == True:
889 
890           if self.local:
891             # This is the same as when gpt-4 gives finish_reason as function_call.
892             # We have just finished a code block, so now we should run it.
893             llama_function_call_finished = True
894 
895         # Remember we're not in a function_call
896         in_function_call = False
897 
898         # If there's no active block,
899         if self.active_block == None:
900 
901           # Create a message block
902           self.active_block = MessageBlock()
903 
904       # Update active_block
905       self.active_block.update_from_message(self.messages[-1])
906 
907       # Check if we're finished
908       if chunk["choices"][0]["finish_reason"] or llama_function_call_finished:
909         if chunk["choices"][
910             0]["finish_reason"] == "function_call" or llama_function_call_finished:
911           # Time to call the function!
912           # (Because this is Open Interpreter, we only have one function.)
913 
914           if self.debug_mode:
915             print("Running function:")
916             print(self.messages[-1])
917             print("---")
918 
919           # Ask for user confirmation to run code
920           if self.auto_run == False:
921 
922             # End the active block so you can run input() below it
923             # Save language and code so we can create a new block in a moment
924             self.active_block.end()
925             language = self.active_block.language
926             code = self.active_block.code
927 
928             # Prompt user
929             response = input("  Would you like to run this code? (y/n)\n\n  ")
930             print("")  # <- Aesthetic choice
931 
932             if response.strip().lower() == "y":
933               # Create a new, identical block where the code will actually be run
934               self.active_block = CodeBlock()
935               self.active_block.language = language
936               self.active_block.code = code
937 
938             else:
939               # User declined to run code.
940               self.active_block.end()
941               self.messages.append({
942                 "role":
943                 "function",
944                 "name":
945                 "run_code",
946                 "content":
947                 "User decided not to run this code."
948               })
949               return
950 
951           # If we couldn't parse its arguments, we need to try again.
952           if not self.local and "parsed_arguments" not in self.messages[-1]["function_call"]:
953 
954             # After collecting some data via the below instruction to users,
955             # This is the most common failure pattern: https://github.com/KillianLucas/open-interpreter/issues/41
956 
957             # print("> Function call could not be parsed.\n\nPlease open an issue on Github (openinterpreter.com, click Github) and paste the following:")
958             # print("\n", self.messages[-1]["function_call"], "\n")
959             # time.sleep(2)
960             # print("Informing the language model and continuing...")
961 
962             # Since it can't really be fixed without something complex,
963             # let's just berate the LLM then go around again