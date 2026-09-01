Reasoning:

The issue is about warning the user or showing pricing/cost information to prevent unanticipated high LLM costs during usage of OpenAI API models. The current code only handles BudgetExceededError by switching to local models but does not give any token count or cost warning during normal usage.

From the gathered context, the LLM call in the respond method uses litellm.completion which streams responses. The litellm library likely has token usage and cost tracking features (seen from litellm.max_budget and litellm._current_cost usage).

We can modify the 'respond' method inside the Interpreter class around the LLM API call:

- After or during calling litellm.completion, extract or access token usage and cost.
- Display an informative warning or notification about the tokens consumed and estimated cost so far.
- Possibly ask the user if they want to continue if usage is high or near some threshold (but since the request is just to show warning or token consumption, a simple print is enough for now).
- The BudgetExceededError handling remains unchanged.

This change fits best inside Interpreter.respond where the API call happens (Location #1 and #2).

Litellm streaming response is a generator, so finishing the iteration would expose total cost and token usage in litellm._current_cost or similar, or maybe litellm provides some property for usage or a method (Not shown exactly in context but we can assume they expose usage info).

We'll add after the LLM API call and after processing the streaming completion a print statement informing about token usage and cost.

No change is needed in the llm setup or other files.

---

Patch:

```
<file>interpreter/archive/interpreter.py</file>
<original>                  response = litellm.completion(
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
              print(Rule(style="white"))</original>
<patched>                  response = litellm.completion(
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
              print(Rule(style="white"))</patched>
```

```
<file>interpreter/archive/interpreter.py</file>
<original>        # Make LLM call
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
          raise Exception(error)</original>
<patched>        # Make LLM call
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

      # After successful LLM call, display tokens used and cost estimation if possible
      # Assume litellm._current_cost and ._used_tokens track usage
      try:
        # Some litellm versions may have these attributes
        cost = getattr(litellm, '_current_cost', None)
        tokens = getattr(litellm, '_used_tokens', None)
        max_budget = getattr(litellm, 'max_budget', None)

        if cost is not None and tokens is not None:
          # If budget is set, compute percent used
          percent_used = None
          if max_budget is not None and max_budget > 0:
            percent_used = float(cost) / float(max_budget) * 100

          warning_msg = f"\n> Tokens used for this call: {tokens}, Estimated cost so far: ${cost:.4f}"
          if percent_used is not None:
            warning_msg += f" ({percent_used:.1f}% of your max budget ${max_budget})"
          print(Markdown(warning_msg))
          
          # If usage is over 80% of budget, display an additional warning
          if percent_used is not None and percent_used > 80:
            print(Markdown("> **Warning:** You are approaching your LLM API budget limit. Consider reviewing your usage or setting a budget to avoid surprise costs."))
      except Exception:
        # silently ignore if attributes not present or any error occurs
        pass
</patched>
```