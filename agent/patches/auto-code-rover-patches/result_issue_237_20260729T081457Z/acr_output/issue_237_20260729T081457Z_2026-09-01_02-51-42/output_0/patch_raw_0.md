The main issue is that `response.metadata.xxx` fields' types (for example, `eliminate`) are unstable: sometimes they are booleans, sometimes strings. This instability leads to unreliable type hinting and unexpected behaviors.

To fix this, we should introduce explicit typing for the `metadata` attribute of `MessageBase`, using a `TypedDict` to define metadata keys and their stable types (e.g., `eliminate` should be `bool`). This will improve type safety and ensure stable typing for metadata fields.

Because `MessageBase` currently inherits from `dict` and stores any extra fields (including metadata) by updating `kwargs`, it would be good to explicitly have a `metadata` dictionary attribute with a proper type. We can add this attribute and handle `metadata` separately so that metadata keys have consistent types. 

We will:
- Import `TypedDict` and `Optional` for typing.
- Define a `MessageMetadata` TypedDict with keys like "eliminate" typed as `bool` (can expand if other keys become known).
- Add a `metadata` attribute of type `MessageMetadata` (or more generically `dict[str, Any]` with the TypedDict).
- From `kwargs`, separate metadata keys to assign them into `self.metadata` with type safety. 
- Retain existing other fields in `kwargs` if any.
This approach will preserve existing functionality but make `metadata` strongly typed and stable.

Since in the code snippet `MessageBase` uses `kwargs` as arbitrary fields, we need to handle this carefully. We can check if kwargs contain a `metadata` key with dict value, and enforce types there. 

This change adds clarity on metadata typing without intrusive refactoring.

---

# modification 1
```
<file>src/agentscope/message.py</file>
<original>14 class MessageBase(dict):
15     """Base Message class, which is used to maintain information for dialog,
16     memory and used to construct prompt.
17     """
</original>
<patched>14 from typing import TypedDict, Optional, Any, Union, Sequence, Literal
15 
16 class MessageMetadata(TypedDict, total=False):
17     eliminate: bool
18     # Other metadata keys can be added here as needed
19 
20 class MessageBase(dict):
21     """Base Message class, which is used to maintain information for dialog,
22     memory and used to construct prompt.
23     """
</patched>
```

# modification 2
```
<file>src/agentscope/message.py</file>
<original>19     def __init__(
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
<patched>19     def __init__(
20         self,
21         name: str,
22         content: Any,
23         role: Literal["user", "system", "assistant"] = "assistant",
24         url: Optional[Union[Sequence[str], str]] = None,
25         timestamp: Optional[str] = None,
26         *,
27         metadata: Optional[MessageMetadata] = None,
28         **kwargs: Any,
29     ) -> None:
30         """Initialize the message object
31 
32         Args:
33             name (`str`):
34                 The name of who send the message. It's often used in
35                 role-playing scenario to tell the name of the sender.
36             content (`Any`):
37                 The content of the message.
38             role (`Literal["system", "user", "assistant"]`, defaults to "assistant"):
39                 The role of who send the message. It can be one of the
40                 `"system"`, `"user"`, or `"assistant"`. Default to
41                 `"assistant"`.
42             url (`Optional[Union[list[str], str]]`, defaults to None):
43                 A url to file, image, video, audio or website.
44             timestamp (`Optional[str]`, defaults to None):
45                 The timestamp of the message, if None, it will be set to
46                 current time.
47             metadata (`Optional[MessageMetadata]`, defaults to None):
48                 Metadata dictionary with stable typed keys.
49             **kwargs (`Any`):
50                 Other attributes of the message.
51         """  # noqa
52         # id and timestamp will be added to the object as its attributes
53         # rather than items in dict
54         self.id = uuid4().hex
55         if timestamp is None:
56             self.timestamp = _get_timestamp()
57         else:
58             self.timestamp = timestamp
59 
60         self.name = name
61         self.content = content
62         self.role = role
63 
64         if url:
65             self.url = url
66         else:
67             self.url = None
68 
69         # Assign metadata with type safety
70         if metadata is not None:
71             self.metadata: MessageMetadata = metadata
72         else:
73             # Initialize empty metadata dict
74             self.metadata: MessageMetadata = {}
75 
76         # Remove metadata key from kwargs if present to avoid duplication
77         if "metadata" in kwargs:
78             kwargs.pop("metadata")
79 
80         # Add remaining kwargs to dict attributes
81         self.update(kwargs)
</patched>
```

# modification 3
```
<file>src/agentscope/message.py</file>
<original>67     def __getattr__(self, key: Any) -> Any:
68         try:
69             return self[key]
70         except KeyError as e:
71             raise AttributeError(f"no attribute '{key}'") from e
72 
73     def __setattr__(self, key: Any, value: Any) -> None:
74         self[key] = value
75 
76     def __delattr__(self, key: Any) -> None:
77         try:
78             del self[key]
79         except KeyError as e:
80             raise AttributeError(f"no attribute '{key}'") from e
</original>
<patched>67     def __getattr__(self, key: Any) -> Any:
68         # Return from instance dict if attribute exists (like metadata)
69         if key in self.__dict__:
70             return self.__dict__[key]
71         try:
72             return self[key]
73         except KeyError as e:
74             raise AttributeError(f"no attribute '{key}'") from e
75 
76     def __setattr__(self, key: Any, value: Any) -> None:
77         # Assign metadata attribute normally
78         if key == "metadata":
79             object.__setattr__(self, key, value)
80             return
81         self[key] = value
82 
83     def __delattr__(self, key: Any) -> None:
84         if key == "metadata":
85             object.__delattr__(self, key)
86             return
87         try:
88             del self[key]
89         except KeyError as e:
90             raise AttributeError(f"no attribute '{key}'") from e
</patched>
```