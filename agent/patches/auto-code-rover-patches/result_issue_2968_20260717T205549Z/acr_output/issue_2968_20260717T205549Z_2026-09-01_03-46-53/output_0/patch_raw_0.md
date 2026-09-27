```
<file>src/crewai/utilities/llm_utils.py</file>
<original>
30     if isinstance(llm_value, str):
31         try:
32             created_llm = LLM(model=llm_value)
33             return created_llm
34         except Exception as e:
35             print(f"Failed to instantiate LLM with model='{llm_value}': {e}")
36             return None
37 
38     # 3) If llm_value is None, parse environment variables or use default
39     if llm_value is None:
40         return _llm_via_environment_or_fallback()
41 
42     # 4) Otherwise, attempt to extract relevant attributes from an unknown object
43     try:
44         # Extract attributes with explicit types
45         model = (
46             getattr(llm_value, "model", None)
47             or getattr(llm_value, "model_name", None)
48             or getattr(llm_value, "deployment_name", None)
49             or str(llm_value)
50         )
51         temperature: Optional[float] = getattr(llm_value, "temperature", None)
52         max_tokens: Optional[int] = getattr(llm_value, "max_tokens", None)
53         logprobs: Optional[int] = getattr(llm_value, "logprobs", None)
54         timeout: Optional[float] = getattr(llm_value, "timeout", None)
55         api_key: Optional[str] = getattr(llm_value, "api_key", None)
56         base_url: Optional[str] = getattr(llm_value, "base_url", None)
57         api_base: Optional[str] = getattr(llm_value, "api_base", None)
58 
59         created_llm = LLM(
60             model=model,
61             temperature=temperature,
62             max_tokens=max_tokens,
63             logprobs=logprobs,
64             timeout=timeout,
65             api_key=api_key,
66             base_url=base_url,
67             api_base=api_base,
68         )
69         return created_llm
</original>
<patched>
30     import os
31     if isinstance(llm_value, str):
32         try:
33             api_key_env = os.environ.get("AZURE_API_KEY") or os.environ.get("OPENAI_API_KEY")
34             api_base_env = os.environ.get("AZURE_API_BASE")
35             api_version_env = os.environ.get("AZURE_API_VERSION")
36             created_llm = LLM(
37                 model=llm_value,
38                 api_key=api_key_env,
39                 api_base=api_base_env,
40                 api_version=api_version_env,
41             )
42             return created_llm
43         except Exception as e:
44             print(f"Failed to instantiate LLM with model='{llm_value}': {e}")
45             return None
46 
47     # 3) If llm_value is None, parse environment variables or use default
48     if llm_value is None:
49         return _llm_via_environment_or_fallback()
50 
51     # 4) Otherwise, attempt to extract relevant attributes from an unknown object
52     try:
53         import os
54         # Extract attributes with explicit types
55         model = (
56             getattr(llm_value, "model", None)
57             or getattr(llm_value, "model_name", None)
58             or getattr(llm_value, "deployment_name", None)
59             or str(llm_value)
60         )
61         temperature: Optional[float] = getattr(llm_value, "temperature", None)
62         max_tokens: Optional[int] = getattr(llm_value, "max_tokens", None)
63         logprobs: Optional[int] = getattr(llm_value, "logprobs", None)
64         timeout: Optional[float] = getattr(llm_value, "timeout", None)
65 
66         # Prefer explicit attributes, fallback to env vars for Azure keys
67         api_key: Optional[str] = getattr(llm_value, "api_key", None) or os.environ.get("AZURE_API_KEY") or os.environ.get("OPENAI_API_KEY")
68         base_url: Optional[str] = getattr(llm_value, "base_url", None) or os.environ.get("AZURE_API_BASE")
69         api_base: Optional[str] = getattr(llm_value, "api_base", None) or os.environ.get("AZURE_API_BASE")
70         api_version: Optional[str] = getattr(llm_value, "api_version", None) or os.environ.get("AZURE_API_VERSION")
71 
72         created_llm = LLM(
73             model=model,
74             temperature=temperature,
75             max_tokens=max_tokens,
76             logprobs=logprobs,
77             timeout=timeout,
78             api_key=api_key,
79             base_url=base_url,
80             api_base=api_base,
81             api_version=api_version,
82         )
83         return created_llm
</patched>
```

```
<file>src/crewai/cli/create_crew.py</file>
<original>
199                     prompt = details["prompt"]
200                     key_name = details["key_name"]
201                     api_key_value = click.prompt(prompt, default="", show_default=False)
202 
203                     if api_key_value.strip():
204                         env_vars[key_name] = api_key_value
</original>
<patched>
199                     prompt = details["prompt"]
200                     key_name = details["key_name"]
201                     api_key_value = click.prompt(prompt, default="", show_default=False)
202 
203                     if api_key_value.strip():
204                         env_vars[key_name] = api_key_value
205                     # Ensure AZURE_API_KEY is also set as OPENAI_API_KEY for compatibility
206                     if key_name == "AZURE_API_KEY" and api_key_value.strip():
207                         env_vars["OPENAI_API_KEY"] = api_key_value
</patched>
```