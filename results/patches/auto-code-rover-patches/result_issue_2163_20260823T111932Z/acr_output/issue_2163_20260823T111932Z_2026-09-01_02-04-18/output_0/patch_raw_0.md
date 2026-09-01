The issue is that when the model reaches the `max_tokens` limit, a `MaxTokensReachedException` is raised with an error message indicating an "unrecoverable state." This makes it seem as though the agent cannot be reused, which is not desired: hitting the max token limit should be a recoverable condition.

The patch should:

1. Update the exception message to remove the phrase "unrecoverable state" so that it instead provides a neutral message indicating the max tokens limit was reached (recoverable condition).

2. Modify the raised exception so it includes the partial recovered message with incomplete tool uses replaced by error messages (using the existing `recover_message_on_max_tokens_reached` function) so callers can access partial results.

3. In the `MaxTokensReachedException` class, extend it to accept an optional partial message and store it as an attribute.

This approach makes it so that the raised exception carries useful partial content, and the agent's internal state remains intact for reuse afterwards.

---

# modification 1
```
<file>strands-py/src/strands/types/exceptions.py</file>
<original>class MaxTokensReachedException(Exception):
    """Exception raised when the model reaches its maximum token generation limit.

    This exception is raised when the model stops generating tokens because it has reached the maximum number of
    tokens allowed for output generation. This can occur when the model's max_tokens parameter is set too low for
    the complexity of the response, or when the model naturally reaches its configured output limit during generation.
    """

    def __init__(self, message: str):
        """Initialize the exception with an error message and the incomplete message object.

        Args:
            message: The error message describing the token limit issue
        """
        super().__init__(message)</original>
<patched>class MaxTokensReachedException(Exception):
    """Exception raised when the model reaches its maximum token generation limit.

    This exception is raised when the model stops generating tokens because it has reached the maximum number of
    tokens allowed for output generation. This can occur when the model's max_tokens parameter is set too low for
    the complexity of the response, or when the model naturally reaches its configured output limit during generation.

    This exception carries an optional partial message attribute that contains the partial results generated before the limit was reached.
    """

    def __init__(self, message: str, partial_message: dict | None = None):
        """Initialize the exception with an error message and the incomplete message object.

        Args:
            message: The error message describing the token limit issue
            partial_message: Optional partial message generated before token limit was reached
        """
        super().__init__(message)
        self.partial_message = partial_message
</patched>
```

# modification 2
```
<file>strands-py/src/strands/event_loop/event_loop.py</file>
<original>305         try:
306             if stop_reason == "max_tokens":
307                 """
308                 Handle max_tokens limit reached by the model.
309 
310                 When the model reaches its maximum token limit, this represents a potentially unrecoverable
311                 state where the model's response was truncated. By default, Strands fails hard with an
312                 MaxTokensReachedException to maintain consistency with other failure types.
313                 """
314                 raise MaxTokensReachedException(
315                     message=(
316                         "Agent has reached an unrecoverable state due to max_tokens limit. "
317                         "For more information see: "
318                         "https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/#maxtokensreachedexception"
319                     )
320                 )</original>
<patched>305         try:
306             if stop_reason == "max_tokens":
307                 """
308                 Handle max_tokens limit reached by the model.
309 
310                 When the model reaches its maximum token limit, this represents a recoverable
311                 condition where the model's response was truncated. Raise MaxTokensReachedException
312                 including the cleaned partial message so callers can access partial results.
313                 """
314                 partial_msg = recover_message_on_max_tokens_reached(message)
315                 raise MaxTokensReachedException(
316                     message=(
317                         "Agent loop stopped: max_tokens limit reached. "
318                         "For more information see: "
319                         "https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/#maxtokensreachedexception"
320                     ),
321                     partial_message=partial_msg,
322                 )
</patched>
```
