The issue is that `_supports_caching` currently only returns True if the model ID string contains "claude" or "anthropic," which catches system inference profile IDs but not application inference profile ARNs from Bedrock. Application inference profile ARNs will have a different format, starting with "arn:aws:bedrock:" and include "application-inference-profiles", so the method needs to be updated to detect these ARNs and return True for them as well. This ensures that caching can be enabled when using Bedrock application inference profile ARNs.

We should keep the existing logic intact for system inference profile model IDs, and add logic to detect if the model_id is an ARN of an application inference profile, by checking for a substring pattern such as `"arn:aws:bedrock:"` and `"application-inference-profiles"` (case insensitive). This will cover the Bedrock ARN format for application inference profiles.

This is a minimal and robust change addressing the core issue while preserving existing functionality.

Here is the patch:

```
<file>src/strands/models/bedrock.py</file>
<original>    @property
    def _supports_caching(self) -> bool:
        """Whether this model supports prompt caching.

        Returns True for Claude models on Bedrock.
        """
        model_id = self.config.get("model_id", "").lower()
        return "claude" in model_id or "anthropic" in model_id
</original>
<patched>    @property
    def _supports_caching(self) -> bool:
        """Whether this model supports prompt caching.

        Returns True for Claude models on Bedrock or Bedrock application inference profile ARNs.
        """
        model_id = self.config.get("model_id", "").lower()
        # Existing check for system inference profile model IDs
        if "claude" in model_id or "anthropic" in model_id:
            return True

        # Check if model_id is a Bedrock application inference profile ARN
        # Bedrock ARNs start with 'arn:aws:bedrock:' and contain 'application-inference-profiles'
        if model_id.startswith("arn:aws:bedrock:") and "application-inference-profiles" in model_id:
            return True

        return False
</patched>
```