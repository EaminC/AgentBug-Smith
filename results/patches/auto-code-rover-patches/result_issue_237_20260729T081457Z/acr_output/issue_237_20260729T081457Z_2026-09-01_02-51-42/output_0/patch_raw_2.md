Reasoning:

The core issue is that the type of `response.metadata.xxx` is unstable, showing sometimes as str ("true"/"false") and sometimes as bool (True/False). To stabilize and type-hint metadata properly, it is best to explicitly add a typed `metadata` attribute to the `MessageBase` class, ideally using a `TypedDict`. This change will improve the typing guarantees and developer experience.

- In `src/agentscope/message.py`, I will define a `MessageMetadata` `TypedDict` with optional known keys having stable types, e.g., `eliminate: bool`. This can be expanded later with other metadata keys.
- Add a `metadata` attribute typed as `MessageMetadata` to `MessageBase`.
- Ensure that `kwargs` items go into `metadata` instead of being mixed arbitrarily into the dict instance.
- Adjust `__getattr__` and `__setattr__` to access `metadata` keys properly.
- Keep backward compatibility by storing basic attributes as before.
- The werewolf example in `examples/game_werewolf/prompt.py` already annotates keys such as `eliminate` but only as content hints. Typing metadata inside `MessageBase` is the appropriate place for stable type hints.

This minimal fix clarifies and stabilizes the metadata type for all message responses including werewolf, without changing the example's logic.

Patch:

# modification 1
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
66 
67     def __getattr__(self, key: Any) -> Any:
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
81 
82     def to_str(self) -> str:
83         """Return the string representation of the message"""
84         raise NotImplementedError
85 
86     def serialize(self) -> str:
87         """Return the serialized message."""
88         raise NotImplementedError
</original>
<patched>from typing import TypedDict, Optional
from typing import Any, Literal, Sequence, Union
from uuid import uuid4

class MessageMetadata(TypedDict, total=False):
    eliminate: bool
    resurrect: bool
    finish_discussion: bool
    # Add other metadata keys here as needed with stable types


class MessageBase(dict):
    """Base Message class, which is used to maintain information for dialog,
    memory and used to construct prompt.
    """

    def __init__(
        self,
        name: str,
        content: Any,
        role: Literal["user", "system", "assistant"] = "assistant",
        url: Optional[Union[Sequence[str], str]] = None,
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the message object

        Args:
            name (`str`):
                The name of who send the message. It's often used in
                role-playing scenario to tell the name of the sender.
            content (`Any`):
                The content of the message.
            role (`Literal["system", "user", "assistant"]`, defaults to "assistant"):
                The role of who send the message. It can be one of the
                `"system"`, `"user"`, or `"assistant"`. Default to
                `"assistant"`.
            url (`Optional[Union[list[str], str]]`, defaults to None):
                A url to file, image, video, audio or website.
            timestamp (`Optional[str]`, defaults to None):
                The timestamp of the message, if None, it will be set to
                current time.
            **kwargs (`Any`):
                Other attributes of the message.
        """  # noqa
        # id and timestamp will be added to the object as its attributes
        # rather than items in dict
        self.id = uuid4().hex
        if timestamp is None:
            self.timestamp = _get_timestamp()
        else:
            self.timestamp = timestamp

        self.name = name
        self.content = content
        self.role = role

        if url:
            self.url = url
        else:
            self.url = None

        # Store metadata keys in a typed dict attribute
        self.metadata: MessageMetadata = {}

        # Move recognized metadata keys from kwargs to metadata attribute,
        # others put into self dict as before (if needed)
        for k, v in kwargs.items():
            if k in MessageMetadata.__annotations__:
                # convert strings "true"/"false" to bool for known keys if possible
                if isinstance(v, str) and v.lower() in {"true", "false"}:
                    v_bool = v.lower() == "true"
                    self.metadata[k] = v_bool  # type: ignore
                else:
                    self.metadata[k] = v  # type: ignore
            else:
                self[k] = v

    def __getattr__(self, key: Any) -> Any:
        # check normal dict keys first
        try:
            return self[key]
        except KeyError:
            # then look in metadata
            if key == "metadata":
                return self.__dict__.get("metadata", {})
            if key in getattr(self, "metadata", {}):
                return self.metadata[key]  # type: ignore
        raise AttributeError(f"no attribute '{key}'")

    def __setattr__(self, key: Any, value: Any) -> None:
        # known basic attributes
        if key in {"id", "timestamp", "name", "content", "role", "url", "metadata"}:
            super().__setattr__(key, value)
        elif key in MessageMetadata.__annotations__:
            # set metadata keys into metadata dict
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                value_bool = value.lower() == "true"
                self.metadata[key] = value_bool  # type: ignore
            else:
                self.metadata[key] = value  # type: ignore
        else:
            self[key] = value

    def __delattr__(self, key: Any) -> None:
        if key in self:
            del self[key]
        elif key in getattr(self, "metadata", {}):
            del self.metadata[key]  # type: ignore
        elif key in self.__dict__:
            del self.__dict__[key]
        else:
            raise AttributeError(f"no attribute '{key}'")

    def to_str(self) -> str:
        """Return the string representation of the message"""
        raise NotImplementedError

    def serialize(self) -> str:
        """Return the serialized message."""
        raise NotImplementedError
</patched>
</file>
```