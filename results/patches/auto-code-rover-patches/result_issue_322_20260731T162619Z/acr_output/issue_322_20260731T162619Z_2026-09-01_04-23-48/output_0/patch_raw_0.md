The reasoning:
The OpenAI streaming gpt-4 or chat completions response provides token usage information only once the response is fully returned; it's often available in the final chunk or via a separate response attribute after finishing the iteration. In the current code, the stream is consumed via a for loop, but there is no extraction of the usage tokens. To get usage tokens, normally the API returns a top-level "usage" field in the response metadata (when stream=False). However, in streaming mode, usage info may not be in every chunk but typically in the last chunk when `finish_reason` is set.

A robust approach is to accumulate the last chunk, extract the usage field if present, or, more simply, after the iteration we can call the API synchronously without streaming just to obtain usage - but that duplicates cost and is not efficient.

Upon examining the current OpenAI Python client behavior, the streaming response is a generator of chunks. Each chunk is similar to the regular response but partial. For streamed chat completions, the usage info comes with the last chunk usually under "usage".

So, we can modify the code to capture the last chunk fully, and after finishing the loop, parse the usage tokens and log/print them.

We can:
- Keep the existing stream iteration for printing.
- Save the last chunk received.
- After finishing printing messages, check if the last chunk has the "usage" field.
- If so, extract "total_tokens" and log or print it.
- Return messages as before.

This minimally changes functionality by adding token usage logging and printing for benchmarking.

---

Patch:

```
<file>gpt_engineer/ai.py</file>
<original>    def next(self, messages: List[Dict[str, str]], prompt=None):
        if prompt:
            messages += [{"role": "user", "content": prompt}]

        logger.debug(f"Creating a new chat completion: {messages}")
        response = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            model=self.model,
            temperature=self.temperature,
        )

        chat = []
        for chunk in response:
            delta = chunk["choices"][0]["delta"]  # type: ignore
            msg = delta.get("content", "")
            print(msg, end="")
            chat.append(msg)
        print()
        messages += [{"role": "assistant", "content": "".join(chat)}]
        logger.debug(f"Chat completion finished: {messages}")
        return messages
</original>
<patched>    def next(self, messages: List[Dict[str, str]], prompt=None):
        if prompt:
            messages += [{"role": "user", "content": prompt}]

        logger.debug(f"Creating a new chat completion: {messages}")
        response = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            model=self.model,
            temperature=self.temperature,
        )

        chat = []
        last_chunk = None
        for chunk in response:
            last_chunk = chunk  # save last chunk for usage info
            delta = chunk["choices"][0]["delta"]  # type: ignore
            msg = delta.get("content", "")
            print(msg, end="")
            chat.append(msg)
        print()

        # Try to extract token usage if available from last chunk
        usage = None
        if last_chunk and "usage" in last_chunk:
            usage = last_chunk["usage"]

        if usage and "total_tokens" in usage:
            total_tokens = usage["total_tokens"]
            print(f"\n[Tokens used: {total_tokens}]")
            logger.info(f"Tokens used in the request: {total_tokens}")

        messages += [{"role": "assistant", "content": "".join(chat)}]
        logger.debug(f"Chat completion finished: {messages}")
        return messages
</patched>
```