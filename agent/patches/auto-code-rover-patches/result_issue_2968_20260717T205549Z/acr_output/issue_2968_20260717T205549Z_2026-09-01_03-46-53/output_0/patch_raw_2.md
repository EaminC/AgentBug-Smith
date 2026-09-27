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
33             api_key_from_env = os.getenv("AZURE_API_KEY") or os.getenv("OPENAI_API_KEY")
34             api_base_from_env = os.getenv("AZURE_API_BASE")
35             api_version_from_env = os.getenv("AZURE_API_VERSION")
36             created_llm = LLM(
37                 model=llm_value,
38                 api_key=api_key_from_env,
39                 api_base=api_base_from_env,
40                 api_version=api_version_from_env,
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
53         # Extract attributes with explicit types
54         import os
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
65         api_key: Optional[str] = getattr(llm_value, "api_key", None) or os.getenv("AZURE_API_KEY") or os.getenv("OPENAI_API_KEY")
66         base_url: Optional[str] = getattr(llm_value, "base_url", None) or os.getenv("AZURE_API_BASE")
67         api_base: Optional[str] = getattr(llm_value, "api_base", None) or os.getenv("AZURE_API_BASE")
68         api_version: Optional[str] = getattr(llm_value, "api_version", None) or os.getenv("AZURE_API_VERSION")
69 
70         created_llm = LLM(
71             model=model,
72             temperature=temperature,
73             max_tokens=max_tokens,
74             logprobs=logprobs,
75             timeout=timeout,
76             api_key=api_key,
77             base_url=base_url,
78             api_base=api_base,
79             api_version=api_version,
80         )
81         return created_llm
</patched>
```
