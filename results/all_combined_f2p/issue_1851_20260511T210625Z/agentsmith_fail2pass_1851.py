import re
import pytest
from aider import prompts

def test_commit_system_prompt_is_one_line_and_imperative():
    """
    Test that the commit_system prompt enforces a one-line, imperative commit message.
    This test checks that the prompt instructions include the imperative mood requirement,
    and that the prompt text itself does not encourage multi-line or verbose output.

    The bug was that commit messages often started with an unuseful line or extra text,
    indicating the prompt was not constraining the model to produce a single concise line.

    After the fix, the prompt explicitly states:
    - Generate a one-line commit message
    - Use imperative mood
    - Reply only with the one-line commit message, no extra text or line breaks
    """

    prompt = prompts.commit_system

    # Check that the prompt mentions imperative mood
    assert re.search(r'imperative mood', prompt, re.IGNORECASE), "Prompt must require imperative mood"

    # Check that the prompt requires one-line commit message only
    assert re.search(r'one-line commit message', prompt, re.IGNORECASE), "Prompt must require one-line commit message"

    # Check that the prompt forbids additional text or line breaks in the response
    forbidden_phrases = [
        r'without any additional text',
        r'without quotes',
        r'one line only',
        r'no line breaks',
        r'reply only with the one-line commit message',
    ]
    assert any(re.search(p, prompt, re.IGNORECASE) for p in forbidden_phrases), (
        "Prompt must forbid extra text or line breaks in the commit message response"
    )

    # Check that the prompt mentions the conventional commit types
    conventional_types = ['fix', 'feat', 'build', 'chore', 'ci', 'docs', 'style', 'refactor', 'perf', 'test']
    for ctype in conventional_types:
        assert ctype in prompt, f"Prompt must mention conventional commit type '{ctype}'"

    # Check that the prompt instructs to start with <type>: <description>
    assert re.search(r'should be structured as follows: <type>: <description>', prompt, re.IGNORECASE), (
        "Prompt must instruct commit message structure as <type>: <description>"
    )

@pytest.mark.parametrize("sample_commit_message", [
    "fix: update capital gains calculation",
    "feat: add new user login feature",
    "docs: update README with installation instructions",
    "refactor: simplify calculation logic",
])
def test_sample_commit_messages_match_prompt_rules(sample_commit_message):
    """
    Test that sample commit messages conform to the prompt rules:
    - One line only
    - Starts with a conventional commit type prefix
    - Uses imperative mood (heuristic: no past tense verbs like 'added', 'fixed')
    - Does not exceed 72 characters
    """

    # Check one line only
    assert '\n' not in sample_commit_message, "Commit message must be one line only"

    # Check starts with conventional commit type prefix
    assert re.match(r'^(fix|feat|build|chore|ci|docs|style|refactor|perf|test): ', sample_commit_message), (
        "Commit message must start with a conventional commit type prefix"
    )

    # Check length <= 72 chars
    assert len(sample_commit_message) <= 72, "Commit message must not exceed 72 characters"

    # Heuristic check for imperative mood: no past tense verbs ending with 'ed' at start of description
    description = sample_commit_message.split(': ', 1)[1]
    first_word = description.split()[0].lower()
    assert not first_word.endswith('ed'), "Commit message description should be in imperative mood (not past tense)"

# Mocking openai or other LLM calls is not needed here since we only test the prompt text and example messages.

# This test file is designed to fail on the buggy codebase where the prompt does not enforce one-line imperative messages,
# and to pass after the fix where the prompt is updated accordingly.
