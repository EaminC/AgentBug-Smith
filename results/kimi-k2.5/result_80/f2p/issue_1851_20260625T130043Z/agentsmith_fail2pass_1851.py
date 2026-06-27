from aider.prompts import commit_system

def test_commit_system_requires_one_line_only():
    """Test that commit_system prompt requires one-line commit messages without extra text.
    
    This addresses issue #1851 where commit messages often start with unuseful lines
    like "Commit message:" or "Here is the commit message for the changes:".
    """
    # The fixed prompt should explicitly require one-line responses
    assert "one-line" in commit_system.lower() or "one line" in commit_system.lower(), \
        "commit_system should explicitly require one-line commit messages"
    
    # Should have strict instruction to not include additional text/explanations
    assert "without any additional text" in commit_system, \
        "commit_system should forbid additional text in the response"
    
    # Should not have the old, weaker instructions that allowed extra text
    assert "Reply with JUST the commit message" not in commit_system, \
        "commit_system should not use the old weak instruction 'Reply with JUST'"
    
    # Should emphasize generating only the commit message, not conversational text
    assert "Reply only with the one-line commit message" in commit_system, \
        "commit_system should use 'Reply only with' to prevent extra conversational text"
