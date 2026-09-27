<file>src/crewai/llm.py</file>
<original>
60 load_dotenv()
</original>
<patched>
60 # Explicitly reload environment variables to ensure updates after .env modifications
61 load_dotenv()
62 
63 # Ensure Azure keys in environment are also available as OPENAI_API_KEY if present
64 import os
65 if "AZURE_API_KEY" in os.environ and "OPENAI_API_KEY" not in os.environ:
66     os.environ["OPENAI_API_KEY"] = os.environ["AZURE_API_KEY"]
</patched>