Reasoning:  
The user wants the script to display warnings or notifications about the tokens consumed or costs incurred during LLM usage, to avoid unexpected cost overruns with OpenAI GPT-4 calls. The relevant code to update is in the `Interpreter.respond` method where the LLM call happens. We can extract token usage or cost info from the response metadata if available.  

Currently, the code just calls `litellm.completion` and streams the response without checking tokens consumed or costs. We want to monitor these and print a warning after the response if consumption is high or near user's budget.  

The litellm library likely provides some usage/cost info in the response or via its internal attributes (e.g. `_current_cost`, or response objects possibly include `usage` fields). We will check for a typical pattern such as `response.usage` or `response['usage']` in chunks. Since streaming, the usage info may appear only at the end or may not be included in the streamed chunks. We can assume litellm.completion returns a generator over chunks (as seen).  

To do this:  
- Accumulate all chunks into a list to process tokens usage metadata after the stream finishes (still yielding the stream chunks as normal).  
- Or alternatively, collect usage info from trailing chunks if possible and after the streaming ends, print estimated tokens and costs.  
- Use `litellm._current_cost` (already used in BudgetExceededError catch) along with tokens consumed to warn the user.  

We will add this additional logic only in the `not self.local` branch, as local Llama inference doesn't involve API calls and cost.  
We will keep the existing error handling and fallback logic as is.  

No changes are needed in other files for now, as the major control lies in `Interpreter.respond`.  

--Patch follows--

# modification 1
```
<file>interpreter/archive/interpreter.py</file>
<original>            
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
648             break</original>
<patched>            
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
627               )
628             else:
629               if self.api_base:
630                 # The user set the api_base. litellm needs this to be "custom/{model}"
631                 response = litellm.completion(
632                   api_base=self.api_base,
633                   model="custom/" + self.model,
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
648             break</patched>
```

# modification 2
```
<file>interpreter/archive/interpreter.py</file>
<original>618         try:
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
<patched>618         try:
619 
620             if self.use_azure:
621               response = litellm.completion(
622                   f"azure/{self.azure_deployment_name}",
623                   messages=messages,
624                   functions=[function_schema],
625                   temperature=self.temperature,
626                   stream=True,
627               )
628             else:
629               if self.api_base:
630                 # The user set the api_base. litellm needs this to be "custom/{model}"
631                 response = litellm.completion(
632                   api_base=self.api_base,
633                   model="custom/" + self.model,
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
648             # Added: Monitor token usage and cost after stream
649             usage_tokens = None
650             total_cost = None
651             # Because streaming returns generator, we collect chunks and then yield
652             chunks = []
653             for chunk in response:
654               chunks.append(chunk)
655               yield chunk
656 
657             # After streaming complete, try to extract usage info:
658             # litellm might put usage info in last chunk or in some attribute
659             # Try to access usage info:
660             usage_data = None
661             if hasattr(response, 'usage'):
662               usage_data = response.usage
663             else:
664               # Possibly usage in last chunk?
665               if chunks and isinstance(chunks[-1], dict):
666                 last_chunk = chunks[-1]
667                 if 'usage' in last_chunk:
668                   usage_data = last_chunk['usage']
669 
670             if usage_data:
671               prompt_tokens = usage_data.get("prompt_tokens", None)
672               completion_tokens = usage_data.get("completion_tokens", None)
673               total_tokens = usage_data.get("total_tokens", None)
674 
675               if prompt_tokens or completion_tokens or total_tokens:
676                 usage_summary = []
677                 if prompt_tokens is not None:
678                   usage_summary.append(f"Prompt tokens: {prompt_tokens}")
679                 if completion_tokens is not None:
680                   usage_summary.append(f"Completion tokens: {completion_tokens}")
681                 if total_tokens is not None:
682                   usage_summary.append(f"Total tokens: {total_tokens}")
683 
684                 print(Markdown(f"> Token usage: {', '.join(usage_summary)}"))
685 
686             # Also print current cost if available via litellm internal tracking
687             current_cost = getattr(litellm, "_current_cost", None)
688             max_budget = getattr(litellm, "max_budget", None)
689             if current_cost is not None:
690               cost_msg = f"Current estimated cost: ${current_cost:.6f}"
691               if max_budget is not None:
692                 cost_msg += f" (Budget: ${max_budget})"
693               print(Markdown(f"> {cost_msg}"))
694 
695             return  # We yielded all chunks already, now stop method here
696 
697         except litellm.BudgetExceededError as e:
698           print(f"Since your LLM API Budget limit was exceeded, you're being switched to local models. Budget: {litellm.max_budget} | Current Cost: {litellm._current_cost}")
699           
700           print(Markdown(
701                 "> Switching to `Code-Llama`...\n\n**Tip:** Run `interpreter --local` to automatically use `Code-Llama`."),
702                     '')
703           time.sleep(2)
704           print(Rule(style="white"))
705 
706 
707 
708           # Temporarily, for backwards (behavioral) compatability, we've moved this part of llama_2.py here.
709           # AND ABOVE.
710           # This way, when folks hit interpreter --local, they get the same experience as before.
711           import inquirer
712 
713           print('', Markdown("**Open Interpreter** will use `Code Llama` for local execution. Use your arrow keys to set up the model."), '')
714 
715           models = {
716               '7B': 'TheBloke/CodeLlama-7B-Instruct-GGUF',
717               '13B': 'TheBloke/CodeLlama-13B-Instruct-GGUF',
718               '34B': 'TheBloke/CodeLlama-34B-Instruct-GGUF'
719           }
720 
721           parameter_choices = list(models.keys())
722           questions = [inquirer.List('param', message="Parameter count (smaller is faster, larger is more capable)", choices=parameter_choices)]
723           answers = inquirer.prompt(questions)
724           chosen_param = answers['param']
725 
726           # THIS is more in line with the future. You just say the model you want by name:
727           self.model = models[chosen_param]
728           self.local = True
729           continue
730         except RateLimitError as rate_error:  # Catch the specific RateLimitError
731             print(Markdown(f"> We hit a rate limit. Cooling off for {attempts} seconds..."))
732             time.sleep(attempts)  
733             max_attempts += 1
734         except Exception as e:  # Catch other exceptions
735             if self.debug_mode:
736               traceback.print_exc()
737             error = traceback.format_exc()
738             time.sleep(3)
739       else:
740         if self.local: 
741           pass
742         else:
743           raise Exception(error)</patched>
```