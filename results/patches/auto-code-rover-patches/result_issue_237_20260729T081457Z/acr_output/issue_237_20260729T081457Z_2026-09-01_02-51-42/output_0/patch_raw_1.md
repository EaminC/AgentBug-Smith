Reasoning:
The issue is about the type of `response.metadata.xxx` being unstable, specifically that the value sometimes is a boolean and sometimes a string representing a boolean. The user expects type hints that indicate the type should be stable, e.g., `eliminate` should be a boolean in metadata.

From the code context, the `MessageBase` class accepts arbitrary extra keyword arguments as keys in the dictionary (via `self.update(kwargs)`), but there's no explicit metadata attribute with typings. To have proper type hints for metadata, we can better separate `metadata` as its own field in `MessageBase`, using a TypedDict that explicitly defines the expected keys and their types.

Also, in the prompt configuration (like in `examples/game_werewolf/prompt.py`), the keys_to_metadata like `eliminate` are used, but they don't have explicit TypedDict definitions in code for type checking. This probably needs a new TypedDict representing the metadata structure for this scenario.

Therefore:
1. Define a TypedDict (e.g., `WerewolfMetadata` or more general `MessageMetadata`) in `src/agentscope/message.py` for the metadata keys like `eliminate: bool`.
2. Adjust the `MessageBase` class to have a typed `metadata` attribute of this type (or a generic one). Preserve other kwargs updating the dict itself.
3. Change `kwargs` processing so that keys recognized as metadata keys go inside `self.metadata` attribute and are typed accordingly, instead of being spread as loose keys in the dict.
4. Provide default empty `metadata` if none is passed.

This approach maintains backward compatibility but adds proper types and clarify that metadata is separated (with stable typing like boolean).

This minimal patch includes:
- Import `TypedDict`, `Optional`.
- Define `class MessageMetadata(TypedDict, total=False)` with `eliminate: bool` as an example.
- Add attribute `self.metadata: MessageMetadata`.
- Cull keys from `kwargs` that are metadata keys and assign to `self.metadata`.
- Keep other keys in the dict.

No changes to other unrelated code.

---

# modification 1: src/agentscope/message.py
```
<file>src/agentscope/message.py</file>
<original>14 class MessageBase(dict):
15     """Base Message class, which is used to maintain information for dialog,
16     memory and used to construct prompt.
17     """
18 
19     def __init__(
20         self,
21         name: str,
22         content: Any,
23         role: Literal["user", "system", "assistant"] = "assistant",
24         url: Optional[Union[Sequence[str], str]] = None,
25         timestamp: Optional[str] = None,
26         **kwargs: Any,
27     ) -> None:
28         """Initialize the message object
29 
30         Args:
31             name (`str`):
32                 The name of who send the message. It's often used in
33                 role-playing scenario to tell the name of the sender.
34             content (`Any`):
35                 The content of the message.
36             role (`Literal["system", "user", "assistant"]`, defaults to "assistant"):
37                 The role of who send the message. It can be one of the
38                 `"system"`, `"user"`, or `"assistant"`. Default to
39                 `"assistant"`.
40             url (`Optional[Union[list[str], str]]`, defaults to None):
41                 A url to file, image, video, audio or website.
42             timestamp (`Optional[str]`, defaults to None):
43                 The timestamp of the message, if None, it will be set to
44                 current time.
45             **kwargs (`Any`):
46                 Other attributes of the message.
47         """  # noqa
48         # id and timestamp will be added to the object as its attributes
49         # rather than items in dict
50         self.id = uuid4().hex
51         if timestamp is None:
52             self.timestamp = _get_timestamp()
53         else:
54             self.timestamp = timestamp
55 
56         self.name = name
57         self.content = content
58         self.role = role
59 
60         if url:
61             self.url = url
62         else:
63             self.url = None
64 
65         self.update(kwargs)
</original>
<patched>from typing import TypedDict, Optional

14 class MessageMetadata(TypedDict, total=False):
15     eliminate: bool
16     # Add other known metadata keys with stable types as needed, e.g.:
17     # resurrect: bool
18     # finish_discussion: bool
19 
20 class MessageBase(dict):
21     """Base Message class, which is used to maintain information for dialog,
22     memory and used to construct prompt.
23     """
24 
25     def __init__(
26         self,
27         name: str,
28         content: Any,
29         role: Literal["user", "system", "assistant"] = "assistant",
30         url: Optional[Union[Sequence[str], str]] = None,
31         timestamp: Optional[str] = None,
32         **kwargs: Any,
33     ) -> None:
34         """Initialize the message object
35 
36         Args:
37             name (`str`):
38                 The name of who send the message. It's often used in
39                 role-playing scenario to tell the name of the sender.
40             content (`Any`):
41                 The content of the message.
42             role (`Literal["system", "user", "assistant"]`, defaults to "assistant"):
43                 The role of who send the message. It can be one of the
44                 `"system"`, `"user"`, or `"assistant"`. Default to
45                 `"assistant"`.
46             url (`Optional[Union[list[str], str]]`, defaults to None):
47                 A url to file, image, video, audio or website.
48             timestamp (`Optional[str]`, defaults to None):
49                 The timestamp of the message, if None, it will be set to
50                 current time.
51             **kwargs (`Any`):
52                 Other attributes of the message.
53         """  # noqa
54         # id and timestamp will be added to the object as its attributes
55         # rather than items in dict
56         self.id = uuid4().hex
57         if timestamp is None:
58             self.timestamp = _get_timestamp()
59         else:
60             self.timestamp = timestamp
61 
62         self.name = name
63         self.content = content
64         self.role = role
65 
66         if url:
67             self.url = url
68         else:
69             self.url = None
70 
71         # Extract metadata keys from kwargs if present and assign
72         meta_keys = set(MessageMetadata.__annotations__.keys())
73         metadata: MessageMetadata = {}
74         remaining_kwargs = {}
75         for k, v in kwargs.items():
76             if k in meta_keys:
77                 # Convert string "true"/"false" to bool for stable typing
78                 if isinstance(v, str):
79                     lowered = v.lower()
80                     if lowered == "true":
81                         metadata[k] = True
82                     elif lowered == "false":
83                         metadata[k] = False
84                     else:
85                         metadata[k] = v  # keep original if can't parse boolean string
86                 else:
87                     metadata[k] = v
88             else:
89                 remaining_kwargs[k] = v
90 
91         self.metadata = metadata
92         self.update(remaining_kwargs)
</patched>
```
