```python
# reproducer.py

import asyncio
import sys

def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


async def main():
    try:
        from crewai import Agent, Crew, Process, Task
        from crewai.tools.snowflake import SnowflakeConfig, SnowflakeSearchTool
        
        # NOTE: Replace these with valid Snowflake credentials for a real test
        snowflake_user = "your_user"
        snowflake_password = "your_password"
        snowflake_account = "your_account"
        snowflake_warehouse = "your_warehouse"
        snowflake_database = "STR"  # use same database in config and tool
        snowflake_schema = "PUBLIC"
        
        # Configuration
        config = SnowflakeConfig(
            user=snowflake_user,
            password=snowflake_password,
            account=snowflake_account,
            warehouse=snowflake_warehouse,
            database=snowflake_database,
            schema=snowflake_schema,
        )
        
        # Initialize tool - Important: do NOT override database/schema here differently than in config,
        # because mismatch might be a source of issue, but reproduce as per user's sample:
        tool = SnowflakeSearchTool(
            config=config,
            pool_size=5,
            max_retries=3,
            enable_caching=True,
            query="SELECT CURRENT_TIMESTAMP();",
            database="STR",
            snowflake_schema="PUBLIC",
        )
        
        # Define agent using the tool
        data_analyst_agent = Agent(
            role="Data Analyst",
            goal="Analyze data from Snowflake database",
            backstory="An expert data analyst who can extract insights from enterprise data.",
            tools=[tool],
            verbose=False,
        )
        
        # Task that requests current time from Snowflake database
        query_task = Task(
            description="Get the current time from snowflake, schema is PUBLIC, Database is STR",
            expected_output="Create a report displaying the current time with the words Current time:::",
            agent=data_analyst_agent,
        )
        
        # Create and run the crew
        crew = Crew(
            agents=[data_analyst_agent],
            tasks=[query_task],
            verbose=False,
            process=Process.sequential,
        )
        
        # Run
        # kickoff() is async per user's code but invoked without await, so we use await here
        result = await crew.kickoff()
        
        # Inspect result - it should contain output including current time result from Snowflake
        found_output = False
        for output in result:
            if isinstance(output, str) and "current time" in output.lower():
                found_output = True
                break
        
        # The reported issue is that the tool output is a coroutine object string and then stops:
        # We use a simple assertion that result is not empty and does not contain the coroutine string.
        if not result:
            raise AssertionError("crew.kickoff() returned no results.")
        coroutine_string = "<coroutine object "
        for r in result:
            if isinstance(r, str) and coroutine_string in r:
                raise AssertionError("Tool returned a coroutine object string instead of query result.")
        
        # If we reach here, it means output was returned and no coroutine object string present
        print("No bug detected: Tool returned query results correctly.")
        sys.exit(0)
    
    except Exception as e:
        print_stacktrace(e)
        # If there's an exception, presume it is due to bug presence or test environment problem
        # Raise AssertionError to mark failure as per instructions
        raise AssertionError("Bug reproduced or error occurred.") from e


if __name__ == "__main__":
    # Run asyncio main and trap AssertionError to exit with code 1 on failure
    try:
        asyncio.run(main())
    except AssertionError as e:
        sys.exit(1)
```
