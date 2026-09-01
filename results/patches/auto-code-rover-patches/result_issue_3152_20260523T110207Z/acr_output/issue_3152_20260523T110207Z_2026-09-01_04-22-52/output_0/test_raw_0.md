```python
# reproducer.py
def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


def main():
    import os
    import sys
    from crewai import Crew, Agent, Task, Process, LLM
    from dotenv import load_dotenv
    from crewai.memory.external.external_memory import ExternalMemory

    # Load environment variables from .env if present
    load_dotenv()

    # Minimal but representative environment setup for Mem0, put your real keys here or in env
    os.environ.setdefault("MEM0_API_KEY", "")
    mem0_api_key = os.environ.get("MEM0_API_KEY")
    mem0_org_id = os.environ.get("MEM0_ORG_ID", "")
    mem0_project_id = os.environ.get("MEM0_PROJECT_ID", "")
    azure_api_key = os.environ.get("AZURE_API_KEY", "")
    azure_api_base = os.environ.get("AZURE_API_BASE", "")

    # We expect keys to be set, else abort early with message
    if not mem0_api_key or not mem0_org_id or not mem0_project_id or not azure_api_key or not azure_api_base:
        msg = (
            "Please set the following environment variables before running reproducer.py:\n"
            "MEM0_API_KEY, MEM0_ORG_ID, MEM0_PROJECT_ID, AZURE_API_KEY, AZURE_API_BASE\n"
            "You can also put them in a .env file."
        )
        print(msg, file=sys.stderr)
        sys.exit(1)

    try:
        chat_agent = Agent(
            role="Friendly chatbot assistant",
            goal="Engage in useful and interesting conversations with users while remembering context.",
            backstory="You are a kind and knowledgeable chatbot assistant. You excel at understanding user needs, providing helpful responses, and maintaining engaging conversations. You remember previous interactions to provide a personalized experience.",
            llm=LLM("azure/gpt-4.1"),
            verbose=True,
        )
        chat_task = Task(
            description="Respond to user conversation. User message: {user_msg}",
            expected_output="Contextually appropriate, helpful, and friendly response.",
            agent=chat_agent,
        )
        external_memory = ExternalMemory(
            embedder_config={
                "provider": "mem0",
                "config": {
                    "user_id": "user-123",
                    "org_id": mem0_org_id,
                    "project_id": mem0_project_id,
                },
            }
        )
        chat_crew = Crew(
            agents=[chat_agent],
            tasks=[chat_task],
            process=Process.sequential,
            external_memory=external_memory,
            verbose=True,
            embedder={
                "provider": "openai",
                "config": {
                    "api_key": azure_api_key,
                    "api_base": azure_api_base,
                    "api_type": "azure",
                    "api_version": "2023-05-15",
                    "model": "text-embedding-ada-002",
                    "deployment_id": "text-embedding-ada-002",
                },
            },
        )

        # Try to kickoff with sample input and trigger memory saving
        user_msg = "Hello! This is a test message to check external memory saving."
        bot_reply = chat_crew.kickoff(inputs={"user_msg": user_msg})

        # Since issue triggers on memory save failure, check logs in verbose output to validate
        # Optionally, test the memory saved by any means if API exposes retrieval
        # But minimal reproduction: if no exception raised, exit 0
        print("✅ External memory saving worked without raising an error.")
        sys.exit(0)

    except Exception as e:
        # Print stacktrace nicely
        print_stacktrace(e)

        # Check if the error message relates to the known mem0 issue message
        err_message = str(e)
        if "Expected a list of items but got type \"str\"" in err_message:
            # Known mem0 bug reproduced
            print("\nBug reproduced: Memory save failed due to invalid 'items' type in API request.", file=sys.stderr)
            raise AssertionError(
                "Memory cannot be saved when using mem0 - reproducer detected the issue"
            ) from e
        else:
            # Unknown error, re-raise for visibility
            raise


if __name__ == "__main__":
    main()
```
