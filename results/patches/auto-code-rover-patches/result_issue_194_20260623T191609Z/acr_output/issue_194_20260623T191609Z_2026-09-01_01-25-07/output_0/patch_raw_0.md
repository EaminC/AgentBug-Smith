Reasoning:
The problem is when loading memories from a JSON file or list/dict input, the loaded memory objects remain dictionaries rather than being converted into Msg instances. This causes errors later because the rest of the system expects Message instances with attributes and methods.

The best place to fix this is inside the TemporaryMemory.add method: before adding each memory unit, if it is a dict (or not a Msg object), convert it to a Msg instance. This is better than fixing at load, because there are multiple entry points that may call add, so add should be the canonical place to ensure the memory units are Msg instances.

We need to import Msg. Then, update the add method to check if each memory_unit is a dict. If so, extract expected fields (name, content, role, timestamp, url, etc.) and create a Msg instance accordingly. Then proceed as before with embedding check and appending to _content.

No other changes are needed.

Patch:

```
<file>src/agentscope/memory/temporary_memory.py</file>
<original>41     def add(
42         self,
43         memories: Union[Sequence[dict], dict, None],
44         embed: bool = False,
45     ) -> None:
46         if memories is None:
47             return
48 
49         if not isinstance(memories, list):
50             record_memories = [memories]
51         else:
52             record_memories = memories
53 
54         # if memory doesn't have id attribute, we skip the checking
55         memories_idx = set(_.id for _ in self._content if hasattr(_, "id"))
56         for memory_unit in record_memories:
57             # add to memory if it's new
58             if (
59                 not hasattr(memory_unit, "id")
60                 or memory_unit.id not in memories_idx
61             ):
62                 if embed:
63                     if self.embedding_model:
64                         # TODO: embed only content or its string representation
65                         memory_unit.embedding = self.embedding_model(
66                             [memory_unit],
67                             return_embedding_only=True,
68                         )
69                     else:
70                         raise RuntimeError("Embedding model is not provided.")
71                 self._content.append(memory_unit)
</original>
<patched>from agentscope.message import Msg

41     def add(
42         self,
43         memories: Union[Sequence[dict], dict, None],
44         embed: bool = False,
45     ) -> None:
46         if memories is None:
47             return
48 
49         if not isinstance(memories, list):
50             record_memories = [memories]
51         else:
52             record_memories = memories
53 
54         # if memory doesn't have id attribute, we skip the checking
55         memories_idx = set(_.id for _ in self._content if hasattr(_, "id"))
56         for memory_unit in record_memories:
57             # Convert dict to Msg if needed
58             if isinstance(memory_unit, dict):
59                 memory_unit = Msg(
60                     name=memory_unit.get("name", None),
61                     content=memory_unit.get("content"),
62                     role=memory_unit.get("role", "user"),
63                     create_time=memory_unit.get("create_time", None),
64                     url=memory_unit.get("url", None),
65                 )
66 
67             # add to memory if it's new
68             if (
69                 not hasattr(memory_unit, "id")
70                 or memory_unit.id not in memories_idx
71             ):
72                 if embed:
73                     if self.embedding_model:
74                         # TODO: embed only content or its string representation
75                         memory_unit.embedding = self.embedding_model(
76                             [memory_unit],
77                             return_embedding_only=True,
78                         )
79                     else:
80                         raise RuntimeError("Embedding model is not provided.")
81                 self._content.append(memory_unit)
</patched>
```