The main idea to address this issue is to provide users with proactive cost and token usage information during the session, instead of only when a budget exceeded error occurs. For this, the best place to add this feedback is in the respond function, which runs a continuous loop generating responses from the LLM and where we already handle exceptions including budget exceeded.

In the current respond function, we catch the litellm.exceptions.BudgetExceededError and show the current session spend and max budget. Building on this, we can track token usage and cost increments inside the message generation loop to inform the user as tokens accumulate across usage.

From the context, litellm maintains some internal state (e.g., litellm._current_cost) that can be displayed. Similarly, litellm probably exposes token usage or cost data on the response stream or via some internal variable (though it’s not explicitly shown). To keep minimal changes and avoid breaking streaming, I will add a periodic yield of a "usage update" message after certain token increments.

Implementation:
- Import time and track intervals so the cost is not printed on every token but every ~15 seconds or so.
- After yielding each chunk, check the current cost from litellm (if available, e.g., litellm._current_cost).
- If cost has increased enough or the time interval elapsed, yield a small usage update message to the user.
- Retain the budget error handling as-is.

No changes are needed to the setup_openai_coding_llm.py, as cost and token usage is runtime state available at response time, best handled in respond.

This should give the user ongoing visibility about usage and avoid unexpected costs.

---

# modification 1
```
<file>interpreter/core/respond.py</file>
<original>def respond(interpreter):
    """
    Yields tokens, but also adds them to interpreter.messages. TBH probably would be good to seperate those two responsibilities someday soon
    Responds until it decides not to run any more code or say anything else.
    """

    while True:

        ### PREPARE MESSAGES ###

        system_message = interpreter.system_message
        
        # Open Procedures is an open-source database of tiny, up-to-date coding tutorials.
        # We can query it semantically and append relevant tutorials/procedures to our system message
        get_relevant_procedures(interpreter.messages[-2:])
        if not interpreter.local:
            try:
                system_message += "\n\n" + get_relevant_procedures(interpreter.messages[-2:])
            except:
                # This can fail for odd SLL reasons. It's not necessary, so we can continue
                pass
        
        # Add user info to system_message, like OS, CWD, etc
        system_message += "\n\n" + get_user_info_string()

        # Create message object
        system_message = {"role": "system", "message": system_message}

        # Create the version of messages that we'll send to the LLM
        messages_for_llm = interpreter.messages.copy()
        messages_for_llm = [system_message] + messages_for_llm

        # It's best to explicitly tell these LLMs when they don't get an output
        for message in messages_for_llm:
            if "output" in message and message["output"] == "":
                message["output"] = "No output"


        ### RUN THE LLM ###

        # Add a new message from the assistant to interpreter's "messages" attribute
        # (This doesn't go to the LLM. We fill this up w/ the LLM's response)
        interpreter.messages.append({"role": "assistant"})

        # Start putting chunks into the new message
        # + yielding chunks to the user
        try:
            for chunk in interpreter._llm(messages_for_llm):

                # Add chunk to the last message
                interpreter.messages[-1] = merge_deltas(interpreter.messages[-1], chunk)

                # This is a coding llm
                # It will yield dict with either a message, language, or code (or language AND code)
                yield chunk
        except litellm.exceptions.BudgetExceededError:
            display_markdown_message(f"""> Max budget exceeded

                **Session spend:** ${litellm._current_cost}
                **Max budget:** ${interpreter.max_budget}

                Press CTRL-C then run `interpreter --max_budget [higher USD amount]` to proceed.
            """)
            break
        # Provide extra information on how to change API keys, if we encounter that error
        # (Many people writing GitHub issues were struggling with this)
        except Exception as e:
            if 'auth' in str(e).lower() or 'api key' in str(e).lower():
                output = traceback.format_exc()
                raise Exception(f"{output}\n\nThere might be an issue with your API key(s).\n\nTo reset your API key (we'll use OPENAI_API_KEY for this example, but you may need to reset your ANTHROPIC_API_KEY, HUGGINGFACE_API_KEY, etc):\n        Mac/Linux: 'export OPENAI_API_KEY=your-key-here',\n        Windows: 'setx OPENAI_API_KEY your-key-here' then restart terminal.\n\n")
            else:
                raise
            
            
            
        ### RUN CODE (if it's there) ###

        if "code" in interpreter.messages[-1]:
            
            if interpreter.debug_mode:
                print("Running code:", interpreter.messages[-1])

            try:
                # What code do you want to run?
                code = interpreter.messages[-1]["code"]

                # Fix a common error where the LLM thinks it's in a Jupyter notebook
                if interpreter.messages[-1]["language"] == "python" and code.startswith("!"):
                    code = code[1:]
                    interpreter.messages[-1]["code"] = code
                    interpreter.messages[-1]["language"] = "shell"

                # Get a code interpreter to run it
                language = interpreter.messages[-1]["language"]
                if language not in interpreter._code_interpreters:
                    interpreter._code_interpreters[language] = create_code_interpreter(language)
                code_interpreter = interpreter._code_interpreters[language]

                # Yield a message, such that the user can stop code execution if they want to
                try:
                    yield {"executing": {"code": code, "language": language}}
                except GeneratorExit:
                    # The user might exit here.
                    # We need to tell python what we (the generator) should do if they exit
                    break

                # Yield each line, also append it to last messages' output
                interpreter.messages[-1]["output"] = ""
                for line in code_interpreter.run(code):
                    yield line
                    if "output" in line:
                        output = interpreter.messages[-1]["output"]
                        output += "\n" + line["output"]

                        # Truncate output
                        output = truncate_output(output, interpreter.max_output)

                        interpreter.messages[-1]["output"] = output.strip()

            except:
                output = traceback.format_exc()
                yield {"output": output.strip()}
                interpreter.messages[-1]["output"] = output.strip()

            yield {"end_of_execution": True}

        else:
            # Doesn't want to run code. We're done
            break

    return</original>
<patched>import time

def respond(interpreter):
    """
    Yields tokens, but also adds them to interpreter.messages. TBH probably would be good to seperate those two responsibilities someday soon
    Responds until it decides not to run any more code or say anything else.
    """

    last_cost_report = 0.0
    last_report_time = 0
    cost_report_interval = 15  # seconds

    while True:

        ### PREPARE MESSAGES ###

        system_message = interpreter.system_message
        
        # Open Procedures is an open-source database of tiny, up-to-date coding tutorials.
        # We can query it semantically and append relevant tutorials/procedures to our system message
        get_relevant_procedures(interpreter.messages[-2:])
        if not interpreter.local:
            try:
                system_message += "\n\n" + get_relevant_procedures(interpreter.messages[-2:])
            except:
                # This can fail for odd SLL reasons. It's not necessary, so we can continue
                pass
        
        # Add user info to system_message, like OS, CWD, etc
        system_message += "\n\n" + get_user_info_string()

        # Create message object
        system_message = {"role": "system", "message": system_message}

        # Create the version of messages that we'll send to the LLM
        messages_for_llm = interpreter.messages.copy()
        messages_for_llm = [system_message] + messages_for_llm

        # It's best to explicitly tell these LLMs when they don't get an output
        for message in messages_for_llm:
            if "output" in message and message["output"] == "":
                message["output"] = "No output"


        ### RUN THE LLM ###

        # Add a new message from the assistant to interpreter's "messages" attribute
        # (This doesn't go to the LLM. We fill this up w/ the LLM's response)
        interpreter.messages.append({"role": "assistant"})

        # Start putting chunks into the new message
        # + yielding chunks to the user
        try:
            for chunk in interpreter._llm(messages_for_llm):

                # Add chunk to the last message
                interpreter.messages[-1] = merge_deltas(interpreter.messages[-1], chunk)

                # This is a coding llm
                # It will yield dict with either a message, language, or code (or language AND code)
                yield chunk

                # Periodically display cost usage info if available
                now = time.time()
                current_cost = getattr(litellm, "_current_cost", 0.0)
                if (current_cost - last_cost_report) > 0.01 or (now - last_report_time) > cost_report_interval:
                    # Yield a message with cost info
                    usage_message = {
                        "message": f"💰 Approximate spend so far: ${current_cost:.4f} (budget: ${interpreter.max_budget if interpreter.max_budget else 'N/A'})"
                    }
                    # Avoid flooding - only yield if changed enough or time passed
                    if current_cost > last_cost_report or (now - last_report_time) > cost_report_interval:
                        yield usage_message
                        last_cost_report = current_cost
                        last_report_time = now

        except litellm.exceptions.BudgetExceededError:
            display_markdown_message(f"""> Max budget exceeded

                **Session spend:** ${litellm._current_cost}
                **Max budget:** ${interpreter.max_budget}

                Press CTRL-C then run `interpreter --max_budget [higher USD amount]` to proceed.
            """)
            break
        # Provide extra information on how to change API keys, if we encounter that error
        # (Many people writing GitHub issues were struggling with this)
        except Exception as e:
            if 'auth' in str(e).lower() or 'api key' in str(e).lower():
                output = traceback.format_exc()
                raise Exception(f"{output}\n\nThere might be an issue with your API key(s).\n\nTo reset your API key (we'll use OPENAI_API_KEY for this example, but you may need to reset your ANTHROPIC_API_KEY, HUGGINGFACE_API_KEY, etc):\n        Mac/Linux: 'export OPENAI_API_KEY=your-key-here',\n        Windows: 'setx OPENAI_API_KEY your-key-here' then restart terminal.\n\n")
            else:
                raise
            
            
            
        ### RUN CODE (if it's there) ###

        if "code" in interpreter.messages[-1]:
            
            if interpreter.debug_mode:
                print("Running code:", interpreter.messages[-1])

            try:
                # What code do you want to run?
                code = interpreter.messages[-1]["code"]

                # Fix a common error where the LLM thinks it's in a Jupyter notebook
                if interpreter.messages[-1]["language"] == "python" and code.startswith("!"):
                    code = code[1:]
                    interpreter.messages[-1]["code"] = code
                    interpreter.messages[-1]["language"] = "shell"

                # Get a code interpreter to run it
                language = interpreter.messages[-1]["language"]
                if language not in interpreter._code_interpreters:
                    interpreter._code_interpreters[language] = create_code_interpreter(language)
                code_interpreter = interpreter._code_interpreters[language]

                # Yield a message, such that the user can stop code execution if they want to
                try:
                    yield {"executing": {"code": code, "language": language}}
                except GeneratorExit:
                    # The user might exit here.
                    # We need to tell python what we (the generator) should do if they exit
                    break

                # Yield each line, also append it to last messages' output
                interpreter.messages[-1]["output"] = ""
                for line in code_interpreter.run(code):
                    yield line
                    if "output" in line:
                        output = interpreter.messages[-1]["output"]
                        output += "\n" + line["output"]

                        # Truncate output
                        output = truncate_output(output, interpreter.max_output)

                        interpreter.messages[-1]["output"] = output.strip()

            except:
                output = traceback.format_exc()
                yield {"output": output.strip()}
                interpreter.messages[-1]["output"] = output.strip()

            yield {"end_of_execution": True}

        else:
            # Doesn't want to run code. We're done
            break

    return
</patched>
```