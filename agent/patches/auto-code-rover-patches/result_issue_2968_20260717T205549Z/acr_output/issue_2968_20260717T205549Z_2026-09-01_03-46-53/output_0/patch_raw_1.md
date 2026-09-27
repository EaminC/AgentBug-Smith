```
<file>src/crewai/utilities/llm_utils.py</file>
<original>
38     # 4) Otherwise, attempt to extract relevant attributes from an unknown object
39     try:
40         # Extract attributes with explicit types
41         model = (
42             getattr(llm_value, "model", None)
43             or getattr(llm_value, "model_name", None)
44             or getattr(llm_value, "deployment_name", None)
45             or str(llm_value)
46         )
47         temperature: Optional[float] = getattr(llm_value, "temperature", None)
48         max_tokens: Optional[int] = getattr(llm_value, "max_tokens", None)
49         logprobs: Optional[int] = getattr(llm_value, "logprobs", None)
50         timeout: Optional[float] = getattr(llm_value, "timeout", None)
51         api_key: Optional[str] = getattr(llm_value, "api_key", None)
52         base_url: Optional[str] = getattr(llm_value, "base_url", None)
53         api_base: Optional[str] = getattr(llm_value, "api_base", None)
54 
55         created_llm = LLM(
56             model=model,
57             temperature=temperature,
58             max_tokens=max_tokens,
59             logprobs=logprobs,
60             timeout=timeout,
61             api_key=api_key,
62             base_url=base_url,
63             api_base=api_base,
64         )
65         return created_llm
</original>
<patched>
38     # 4) Otherwise, attempt to extract relevant attributes from an unknown object
39     try:
40         import os
41         # Extract attributes with explicit types
42         model = (
43             getattr(llm_value, "model", None)
44             or getattr(llm_value, "model_name", None)
45             or getattr(llm_value, "deployment_name", None)
46             or str(llm_value)
47         )
48         temperature: Optional[float] = getattr(llm_value, "temperature", None)
49         max_tokens: Optional[int] = getattr(llm_value, "max_tokens", None)
50         logprobs: Optional[int] = getattr(llm_value, "logprobs", None)
51         timeout: Optional[float] = getattr(llm_value, "timeout", None)
52 
53         # For Azure OpenAI, prefer environment variable AZURE_API_KEY if not explicitly set in llm_value
54         api_key: Optional[str] = (
55             getattr(llm_value, "api_key", None)
56             or os.getenv("AZURE_API_KEY")
57             or os.getenv("OPENAI_API_KEY")
58         )
59 
60         base_url: Optional[str] = (
61             getattr(llm_value, "base_url", None)
62             or os.getenv("AZURE_API_BASE")
63             or os.getenv("OPENAI_API_BASE")
64         )
65 
66         api_base: Optional[str] = (
67             getattr(llm_value, "api_base", None)
68             or os.getenv("AZURE_API_BASE")
69             or os.getenv("OPENAI_API_BASE")
70         )
71 
72         api_version: Optional[str] = (
73             getattr(llm_value, "api_version", None)
74             or os.getenv("AZURE_API_VERSION")
75         )
76 
77         created_llm = LLM(
78             model=model,
79             temperature=temperature,
80             max_tokens=max_tokens,
81             logprobs=logprobs,
82             timeout=timeout,
83             api_key=api_key,
84             base_url=base_url,
85             api_base=api_base,
86             api_version=api_version,
87         )
88         return created_llm
</patched>
```

```
<file>src/crewai/llm.py</file>
<original>
290     def __init__(
291         self,
292         model: str,
293         timeout: Optional[Union[float, int]] = None,
294         temperature: Optional[float] = None,
295         top_p: Optional[float] = None,
296         n: Optional[int] = None,
297         stop: Optional[Union[str, List[str]]] = None,
298         max_completion_tokens: Optional[int] = None,
299         max_tokens: Optional[int] = None,
300         presence_penalty: Optional[float] = None,
301         frequency_penalty: Optional[float] = None,
302         logit_bias: Optional[Dict[int, float]] = None,
303         response_format: Optional[Type[BaseModel]] = None,
304         seed: Optional[int] = None,
305         logprobs: Optional[int] = None,
306         top_logprobs: Optional[int] = None,
307         base_url: Optional[str] = None,
308         api_base: Optional[str] = None,
309         api_version: Optional[str] = None,
310         api_key: Optional[str] = None,
311         callbacks: List[Any] = [],
312         reasoning_effort: Optional[Literal["none", "low", "medium", "high"]] = None,
313         stream: bool = False,
314         **kwargs,
315     ):
316         self.model = model
317         self.timeout = timeout
318         self.temperature = temperature
319         self.top_p = top_p
320         self.n = n
321         self.max_completion_tokens = max_completion_tokens
322         self.max_tokens = max_tokens
323         self.presence_penalty = presence_penalty
324         self.frequency_penalty = frequency_penalty
325         self.logit_bias = logit_bias
326         self.response_format = response_format
327         self.seed = seed
328         self.logprobs = logprobs
329         self.top_logprobs = top_logprobs
330         self.base_url = base_url
331         self.api_base = api_base
332         self.api_version = api_version
333         self.api_key = api_key
334         self.callbacks = callbacks
335         self.context_window_size = 0
336         self.reasoning_effort = reasoning_effort
337         self.additional_params = kwargs
338         self.is_anthropic = self._is_anthropic_model(model)
339         self.stream = stream
340 
341         litellm.drop_params = True
342 
343         # Normalize self.stop to always be a List[str]
344         if stop is None:
345             self.stop: List[str] = []
346         elif isinstance(stop, str):
347             self.stop = [stop]
348         else:
349             self.stop = stop
350 
351         self.set_callbacks(callbacks)
352         self.set_env_callbacks()
</original>
<patched>
290     def __init__(
291         self,
292         model: str,
293         timeout: Optional[Union[float, int]] = None,
294         temperature: Optional[float] = None,
295         top_p: Optional[float] = None,
296         n: Optional[int] = None,
297         stop: Optional[Union[str, List[str]]] = None,
298         max_completion_tokens: Optional[int] = None,
299         max_tokens: Optional[int] = None,
300         presence_penalty: Optional[float] = None,
301         frequency_penalty: Optional[float] = None,
302         logit_bias: Optional[Dict[int, float]] = None,
303         response_format: Optional[Type[BaseModel]] = None,
304         seed: Optional[int] = None,
305         logprobs: Optional[int] = None,
306         top_logprobs: Optional[int] = None,
307         base_url: Optional[str] = None,
308         api_base: Optional[str] = None,
309         api_version: Optional[str] = None,
310         api_key: Optional[str] = None,
311         callbacks: List[Any] = [],
312         reasoning_effort: Optional[Literal["none", "low", "medium", "high"]] = None,
313         stream: bool = False,
314         **kwargs,
315     ):
316         import os
317         self.model = model
318         self.timeout = timeout
319         self.temperature = temperature
320         self.top_p = top_p
321         self.n = n
322         self.max_completion_tokens = max_completion_tokens
323         self.max_tokens = max_tokens
324         self.presence_penalty = presence_penalty
325         self.frequency_penalty = frequency_penalty
326         self.logit_bias = logit_bias
327         self.response_format = response_format
328         self.seed = seed
329         self.logprobs = logprobs
330         self.top_logprobs = top_logprobs
331         self.base_url = base_url or os.getenv("AZURE_API_BASE") or os.getenv("OPENAI_API_BASE")
332         self.api_base = api_base or os.getenv("AZURE_API_BASE") or os.getenv("OPENAI_API_BASE")
333         self.api_version = api_version or os.getenv("AZURE_API_VERSION")
334         self.api_key = (
335             api_key
336             or os.getenv("AZURE_API_KEY")
337             or os.getenv("OPENAI_API_KEY")
338         )
339         self.callbacks = callbacks
340         self.context_window_size = 0
341         self.reasoning_effort = reasoning_effort
342         self.additional_params = kwargs
343         self.is_anthropic = self._is_anthropic_model(model)
344         self.stream = stream
345 
346         litellm.drop_params = True
347 
348         # Normalize self.stop to always be a List[str]
349         if stop is None:
350             self.stop: List[str] = []
351         elif isinstance(stop, str):
352             self.stop = [stop]
353         else:
354             self.stop = stop
355 
356         self.set_callbacks(callbacks)
357         self.set_env_callbacks()
</patched>
```