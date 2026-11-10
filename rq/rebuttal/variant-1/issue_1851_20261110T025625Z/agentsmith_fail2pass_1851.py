import re
import pytest
from aider import prompts

def test_commit_system_prompt_one_line_and_imperative():
    """
    This test verifies that the commit_system prompt in aider.prompts.py
    enforces a one-line, imperative mood commit message generation.

    The buggy version allowed multi-line or non-imperative commit messages,
    causing commit messages to start with unuseful lines.

    After the fix, the prompt explicitly instructs to generate a one-line
    imperative commit message without extra text or line breaks.

    This test simulates the prompt usage by checking the prompt text itself
    and by verifying that generated commit messages (simulated here) conform
    to the rules implied by the prompt.
    """

    # The commit_system prompt string should contain instructions enforcing:
    # - One-line output only
    # - Imperative mood
    # - No extra text or line breaks
    prompt = prompts.commit_system

    # Check that the prompt contains key phrases enforcing one-line and imperative
    assert "one-line" in prompt.lower(), "Prompt must require one-line commit message"
    assert "imperative" in prompt.lower(), "Prompt must require imperative mood"
    assert "without any additional text" in prompt.lower() or "without quotes" in prompt.lower(), \
        "Prompt must require no extra text or quotes"

    # Simulate a buggy model output that would cause the problem:
    buggy_outputs = [
        "Here is the commit message for the changes:\nfix: update calculation\n",
        "Commit Message:\nfix: update calculation\n",
        "Got it, here is the commit message:\nfix: update calculation\n",
        "fix: update calculation\n\nAdditional explanation",
    ]

    # The fixed prompt should prevent such multi-line or prefixed outputs.
    # We simulate this by checking that the output is a single line starting with a valid type prefix.

    valid_types = {"fix", "feat", "build", "chore", "ci", "docs", "style", "refactor", "perf", "test"}

    def is_valid_commit_message(msg: str) -> bool:
        # Must be a single line
        lines = msg.strip().splitlines()
        if len(lines) != 1:
            return False
        line = lines[0].strip()
        # Must start with a valid type prefix followed by colon and space
        match = re.match(r"^(fix|feat|build|chore|ci|docs|style|refactor|perf|test):\s.+", line)
        if not match:
            return False
        # Must be imperative mood - we cannot programmatically check mood, but we can check it does not start with past tense words
        # We'll just check it does not start with "Added", "Adding", "Got", "Here is", etc.
        forbidden_starts = ["Added", "Adding", "Got", "Here is", "Commit Message", "Commit message", "fixes", "fixed"]
        for fs in forbidden_starts:
            if line.lower().startswith(fs.lower()):
                return False
        # Length check (<=72 chars)
        if len(line) > 72:
            return False
        return True

    # The buggy outputs should fail the validation
    for output in buggy_outputs:
        assert not is_valid_commit_message(output), f"Buggy output should be invalid: {output!r}"

    # Simulate a correct output that should pass validation
    good_output = "fix: update capital gains calculation"
    assert is_valid_commit_message(good_output), "Valid commit message failed validation"

    # Also test that the prompt ends with instructions to reply only with the one-line commit message
    assert re.search(r"Reply only with the one-line commit message", prompt), \
        "Prompt must instruct to reply only with the one-line commit message"

    # This test ensures that the prompt text and expected commit message format are consistent with the fix.
    # On the buggy codebase, the prompt lacks these instructions and the test will fail.
    # After the fix, the prompt is updated and the test will pass.
