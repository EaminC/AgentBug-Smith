Reasoning:
To transition Mem0 memory to v2 according to the feature request, we need to:
- Accept new config options like `run_id`, `agent_memory_enabled`, `memory_inclusion`, `custom_categories`.
- Support passing `run_id` for short-term memory to associate memory with specific conversation sessions.
- Enable or disable agent memory by optionally omitting `agent_id` in the save and search methods.
- Incorporate new features `memory_inclusion` and `custom_categories` into metadata or parameters when saving.
- Update search to use Mem0 v2 API changes, removing deprecated `output_format`, using filters (metadata), and including `run_id` when applicable.

We'll minimally modify the `__init__` method to extract the new configs and keep them as instance attributes.

We'll update the `save` method to:
- Pass `run_id` if defined and if memory_type is short_term.
- Only send `agent_id` if agent memory is enabled (configurable).
- Add `memory_inclusion` and `custom_categories` params if present in metadata or config.

Update `search` method:
- Remove `output_format` (deprecated).
- Add `run_id` if present as a filter.
- Allow omitting `agent_id` if agent memory is disabled.
- Use the new vocab for filters / metadata.

We'll also add helper functions `_get_run_id()` and `_agent_memory_enabled()` to assist. We'll minimally change existing behavior and maintain backward compatibility.

Patch:

# modification 1
```
<file>src/crewai/memory/storage/mem0_storage.py</file>
<original>    def __init__(self, type, crew=None, config=None):
        super().__init__()
        supported_types = ["user", "short_term", "long_term", "entities", "external"]
        if type not in supported_types:
            raise ValueError(
                f"Invalid type '{type}' for Mem0Storage. Must be one of: "
                + ", ".join(supported_types)
            )

        self.memory_type = type
        self.crew = crew
        self.config = config or {}
        # TODO: Memory config will be removed in the future the config will be passed as a parameter
        self.memory_config = self.config or getattr(crew, "memory_config", {}) or {}

        # User ID is required for user memory type "user" since it's used as a unique identifier for the user.
        user_id = self._get_user_id()
        if type == "user" and not user_id:
            raise ValueError("User ID is required for user memory type")

        # API key in memory config overrides the environment variable
        config = self._get_config()
        mem0_api_key = config.get("api_key") or os.getenv("MEM0_API_KEY")
        mem0_org_id = config.get("org_id")
        mem0_project_id = config.get("project_id")
        mem0_local_config = config.get("local_mem0_config")

        # Initialize MemoryClient or Memory based on the presence of the mem0_api_key
        if mem0_api_key:
            if mem0_org_id and mem0_project_id:
                self.memory = MemoryClient(
                    api_key=mem0_api_key, org_id=mem0_org_id, project_id=mem0_project_id
                )
            else:
                self.memory = MemoryClient(api_key=mem0_api_key)
        else:
            if mem0_local_config and len(mem0_local_config):
                self.memory = Memory.from_config(mem0_local_config)
            else:
                self.memory = Memory()
</original>
<patched>    def __init__(self, type, crew=None, config=None):
        super().__init__()
        supported_types = ["user", "short_term", "long_term", "entities", "external"]
        if type not in supported_types:
            raise ValueError(
                f"Invalid type '{type}' for Mem0Storage. Must be one of: "
                + ", ".join(supported_types)
            )

        self.memory_type = type
        self.crew = crew
        self.config = config or {}
        # TODO: Memory config will be removed in the future the config will be passed as a parameter
        self.memory_config = self.config or getattr(crew, "memory_config", {}) or {}

        # Extract v2-specific parameters from config for convenience
        self.run_id = self._get_config().get("run_id")  # For short-term session memory
        self.agent_memory_enabled = self._get_config().get("agent_memory_enabled", True)
        self.memory_inclusion = self._get_config().get("memory_inclusion")  # e.g. "include_all"
        self.custom_categories = self._get_config().get("custom_categories")  # e.g. list or string

        # User ID is required for user memory type "user" since it's used as a unique identifier for the user.
        user_id = self._get_user_id()
        if type == "user" and not user_id:
            raise ValueError("User ID is required for user memory type")

        # API key in memory config overrides the environment variable
        config = self._get_config()
        mem0_api_key = config.get("api_key") or os.getenv("MEM0_API_KEY")
        mem0_org_id = config.get("org_id")
        mem0_project_id = config.get("project_id")
        mem0_local_config = config.get("local_mem0_config")

        # Initialize MemoryClient or Memory based on the presence of the mem0_api_key
        if mem0_api_key:
            if mem0_org_id and mem0_project_id:
                self.memory = MemoryClient(
                    api_key=mem0_api_key, org_id=mem0_org_id, project_id=mem0_project_id
                )
            else:
                self.memory = MemoryClient(api_key=mem0_api_key)
        else:
            if mem0_local_config and len(mem0_local_config):
                self.memory = Memory.from_config(mem0_local_config)
            else:
                self.memory = Memory()
</patched>
```

# modification 2
```
<file>src/crewai/memory/storage/mem0_storage.py</file>
<original>    def save(self, value: Any, metadata: Dict[str, Any]) -> None:
        user_id = self._get_user_id()
        agent_name = self._get_agent_name()
        assistant_message = [{"role" : "assistant","content" : value}] 
        params = None
        if self.memory_type == "short_term":
            params = {
                "agent_id": agent_name,
                "infer": False,
                "metadata": {"type": "short_term", **metadata},
            }
        elif self.memory_type == "long_term":
            params = {
                "agent_id": agent_name,
                "infer": False,
                "metadata": {"type": "long_term", **metadata},
            }
        elif self.memory_type == "entities":
            params = {
                "agent_id": agent_name,
                "infer": False,
                "metadata": {"type": "entity", **metadata},
            }
        elif self.memory_type == "external":
            params = {
                "user_id": user_id,
                "agent_id": agent_name,
                "metadata": {"type": "external", **metadata},
            }

        if params:
            if isinstance(self.memory, MemoryClient):
                params["output_format"] = "v1.1"
            
            self.memory.add(assistant_message, **params)
</original>
<patched>    def save(self, value: Any, metadata: Dict[str, Any]) -> None:
        user_id = self._get_user_id()
        agent_name = self._get_agent_name()
        assistant_message = [{"role" : "assistant","content" : value}]
        params = None

        # Determine if agent memory enabled
        agent_enabled = self.agent_memory_enabled

        if self.memory_type == "short_term":
            params = {
                # Only set agent_id if agent memory enabled
                **({"agent_id": agent_name} if agent_enabled else {}),
                "infer": False,
                "metadata": {"type": "short_term", **metadata},
            }
            # Add run_id if available for short_term memory v2
            if self.run_id:
                params["run_id"] = self.run_id

        elif self.memory_type == "long_term":
            params = {
                **({"agent_id": agent_name} if agent_enabled else {}),
                "infer": False,
                "metadata": {"type": "long_term", **metadata},
            }
        elif self.memory_type == "entities":
            params = {
                **({"agent_id": agent_name} if agent_enabled else {}),
                "infer": False,
                "metadata": {"type": "entity", **metadata},
            }
        elif self.memory_type == "external":
            params = {
                "user_id": user_id,
                **({"agent_id": agent_name} if agent_enabled else {}),
                "metadata": {"type": "external", **metadata},
            }

        if params:
            # Add new mem0 v2 feature params if present in metadata or config
            if self.memory_inclusion:
                params["memory_inclusion"] = self.memory_inclusion
            if self.custom_categories:
                params["custom_categories"] = self.custom_categories

            if isinstance(self.memory, MemoryClient):
                # v1.1 output_format is deprecated in v2, so omitted here (remove if still needed)
                pass

            self.memory.add(assistant_message, **params)
</patched>
```

# modification 3
```
<file>src/crewai/memory/storage/mem0_storage.py</file>
<original>    def search(
        self,
        query: str,
        limit: int = 3,
        score_threshold: float = 0.35,
    ) -> List[Any]:
        params = {"query": query, "limit": limit, "output_format": "v1.1"}
        if user_id := self._get_user_id():
            params["user_id"] = user_id

        agent_name = self._get_agent_name()
        if self.memory_type == "short_term":
            params["agent_id"] = agent_name
            params["metadata"] = {"type": "short_term"}
        elif self.memory_type == "long_term":
            params["agent_id"] = agent_name
            params["metadata"] = {"type": "long_term"}
        elif self.memory_type == "entities":
            params["agent_id"] = agent_name
            params["metadata"] = {"type": "entity"}
        elif self.memory_type == "external":
            params["agent_id"] = agent_name
            params["metadata"] = {"type": "external"}

        # Discard the filters for now since we create the filters
        # automatically when the crew is created.
        if isinstance(self.memory, Memory):
            del params["metadata"], params["output_format"]
            
        results = self.memory.search(**params)
        return [r for r in results["results"] if r["score"] >= score_threshold]
</original>
<patched>    def search(
        self,
        query: str,
        limit: int = 3,
        score_threshold: float = 0.35,
    ) -> List[Any]:
        # Build base params without deprecated output_format
        params = {"query": query, "limit": limit}

        if user_id := self._get_user_id():
            params["user_id"] = user_id

        agent_name = self._get_agent_name()
        agent_enabled = self.agent_memory_enabled

        # Compose filters for v2 API, these replace 'metadata' from v1
        filters = {"type": self.memory_type if self.memory_type != "entities" else "entity"}

        # Add run_id filter if set and applicable to short_term memories
        if self.memory_type == "short_term" and self.run_id:
            filters["run_id"] = self.run_id

        # Only add agent_id if agent memory enabled and agent_name is present
        if agent_enabled and agent_name:
            params["agent_id"] = agent_name

        # Apply filters to params
        params["filters"] = filters

        # If using local Memory (non-client), clear filters because local does not support filters
        if isinstance(self.memory, Memory):
            params.pop("filters", None)

        results = self.memory.search(**params)
        return [r for r in results.get("results", []) if r["score"] >= score_threshold]
</patched>
```

# modification 4
```
<file>src/crewai/memory/storage/mem0_storage.py</file>
<original>    def _get_user_id(self) -> str:
        return self._get_config().get("user_id", "")
</original>
<patched>    def _get_user_id(self) -> str:
        return self._get_config().get("user_id", "")
    
    def _get_run_id(self) -> str:
        # Return run_id for session-specific short-term memory, if configured
        return getattr(self, "run_id", None)

    def _agent_memory_enabled(self) -> bool:
        # Return if agent memory is enabled (default True)
        return getattr(self, "agent_memory_enabled", True)
</patched>
```

Summary: Added config member variables for new v2 features in `__init__`. Modified `save` to optionally pass `run_id`, omit `agent_id` if agent memory disabled, and add new features params. Modified `search` to use v2 filters, conditionally add run_id, omit agent_id if disabled, and handle local memory backward compatibility. Added helper functions `_get_run_id` and `_agent_memory_enabled`.

This adapts the Mem0 integration to v2 usage with minimal disruption, per the issue request.