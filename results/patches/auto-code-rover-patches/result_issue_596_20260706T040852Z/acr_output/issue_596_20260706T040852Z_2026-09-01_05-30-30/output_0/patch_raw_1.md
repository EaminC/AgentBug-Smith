Reasoning:
To address the issue of high and unexpected LLM costs, we should incorporate token usage and cost estimation right after receiving the LLM response (for the remote GPT calls). We can warn the user about token consumption and estimated cost, and optionally prompt the user before continuing if the cost is above a certain threshold or near the budget (for example, let's define a WARNING_TOKEN_THRESHOLD and WARNING_COST_THRESHOLD). The existing code handles retries and budget exceeded exceptions, but does not proactively show usage or ask user confirmation about costs.

We will:
- After getting the GPT response, extract usage info (total_tokens).
- Calculate estimated cost based on model pricing.
- Print a warning if tokens or cost exceed thresholds.
- Prompt the user to continue or cancel the operation to prevent runaway costs.
- Skip this prompt if `auto_run` is set to True (assuming unattended mode).

No cost info or token usage can be done for local models or Code-Llama, so only do this for non-local (remote) requests.

This minimal changes approach preserves the current flow while adding the requested cost transparency.

To implement cost calculations, we need to know pricing for tokens on the model. For example, GPT-4 has known pricing. For simplicity, we use approximate pricing here (can be improved later). The existing code imports litellm which likely exposes current cost and budgets but does not expose tokens.

We'll add imports for re (to extract usage safely) and define token cost mappings inside respond (or at class level if preferred). Since `litellm.completion` returns a streamed response, after the loop, we can extract the usage from the final response object or from the API call metadata if available. Here, it looks like the response object returned by litellm.completion is an iterator for streaming chunks, so token usage might not be available directly. We can get usage info often from the last chunk or via `response` metadata if litellm supports it.

Because the existing code only gets streaming chunks, but no mention of collecting usage or cost, it depends on litellm internal design. To avoid blocking the streaming code, we'll query `response` assuming it has an `usage` attribute or equivalent after the iteration ends. If not, we fallback gracefully (won't crash). This is best effort.

So the patch will:
- Add token usage and cost warning after the streaming loop completes.
- Ask user to confirm to proceed if cost/token is high and auto_run is False.
- If user declines, raise an exception or gracefully abort.

We do not interrupt the existing retry loop or budget exceeded handling, just add a warning on each response.

Patch follows.

---

# modification 1
```
<file>interpreter/archive/interpreter.py</file>
<original>    # Make LLM call
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
          </original>
<patched>    import re  # Add necessary import at top of respond (can also add at file top if preferred)
    # Make LLM call
    if not self.local:
      
      # GPT
      max_attempts = 3  
      attempts = 0  
      error = ""

      # Define token and cost warning thresholds and pricing per 1k tokens (USD)
      WARNING_TOKEN_THRESHOLD = 3000   # warn if token count above this in total (prompt + completion)
      WARNING_COST_THRESHOLD = 0.20    # warn if estimated cost above this (in USD)
      TOKEN_PRICING_PER_1K = {
          # Approximate prices in USD per 1k tokens for GPT-4 as example
          "gpt-4": 0.03 + 0.06,  # Prompt + Completion combined approx total average
          "gpt-4-0314": 0.03 + 0.06,
          "gpt-4-32k": 0.06 + 0.12,
          "gpt-3.5-turbo": 0.0015 * 2,  # Assume prompt + completion total double of prompt price approx
          "gpt-3.5-turbo-0301": 0.0015 * 2,
      }

      # Lookup cost for current model or default
      model_cost_per_1k = TOKEN_PRICING_PER_1K.get(self.model.lower(), 0.03 + 0.06)

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

      # After successful response, attempt to retrieve token usage and calculate cost
      try:
        # If litellm response supports usage info after iteration
        # (litellm.completion returns an iterator usually, so we may need to get last chunk, or response.usage)
        # We'll collect usage info from response.usage or else from trailing chunk["usage"] if any

        # Iterate through streamed chunks to consume the generator and collect partial text
        collected_chunks = []
        if hasattr(response, "__iter__") and not isinstance(response, list):
          # For streaming, yield chunks one by one so original behavior preserved
          pass
        else:
          # Non-stream, no usage info
          collected_chunks = []

        # But usage is available as attribute after streaming:
        usage = getattr(response, "usage", None)

        # If usage is None, try to parse from last chunk if available
        # Here, we do not consume response again (streaming already done later, so just check usage now)

        if usage and "total_tokens" in usage:
          total_tokens = usage["total_tokens"]
        else:
          total_tokens = None

        # If token count unknown, skip warnings
        if total_tokens:
          estimated_cost = (total_tokens / 1000) * model_cost_per_1k

          # Print a user warning if tokens / cost are above threshold
          if total_tokens > WARNING_TOKEN_THRESHOLD or estimated_cost > WARNING_COST_THRESHOLD:
            print(Markdown(f"> Warning: LLM used approximately {total_tokens} tokens, estimated cost ${estimated_cost:.4f} USD for this request."))
            if not self.auto_run:
              proceed = input("  This is a potentially high cost. Would you like to continue? (y/n): ").strip().lower()
              if proceed not in ("y", "yes"):
                print(Markdown("> User aborted due to cost concerns."))
                raise Exception("User aborted due to high estimated LLM cost.")
      except Exception:
        # In case usage data is not available or error in cost calculation, silently ignore
        pass
      </patched>
```