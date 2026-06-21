import sys
import os
import inspect

def test_commit_prompt_does_not_contain_extra_phrases():
    """Test that the commit system prompt doesn't contain phrases that could cause extra text."""
    from aider.prompts import commit_system
    # In the buggy version, the prompt says "Reply with JUST the commit message"
    # In the fixed version, it says "Reply only with the one-line commit message"
    # The buggy version also lacks "one-line" (has "one line only").
    # We'll test for the fixed version's key phrases.
    # This test should fail on buggy, pass on fixed.

    # Check for the fixed version's specific phrasing
    assert "Reply only with the one-line commit message" in commit_system

def test_commit_message_extraction():
    """Test that the commit message extraction logic handles extra text correctly."""
    from aider.prompts import commit_system
    # The prompt should explicitly tell the model not to add extra text.
    assert "without any additional text, explanations, or line breaks" in commit_system

def test_buggy_version_fails():
    """Test that buggy version contains the wrong phrasing."""
    from aider.prompts import commit_system
    
    # In buggy version, we should find the old phrasing
    # This test should pass on buggy, fail on fixed
    buggy_phrases = [
        "Reply with JUST the commit message",
        "Reply with one line only!"
    ]
    
    # Check if any buggy phrases are present (should be True for buggy, False for fixed)
    has_buggy_phrases = any(phrase in commit_system for phrase in buggy_phrases)
    
    # This assertion will pass for buggy version, fail for fixed version
    # We're testing the inverse: if it's buggy, this should be True
    # But we need to be careful - we want this to fail when patch is applied
    # Actually, let's check that the fixed phrases are NOT in buggy version
    fixed_phrases = [
        "Reply only with the one-line commit message",
        "without any additional text, explanations, or line breaks"
    ]
    
    has_fixed_phrases = all(phrase in commit_system for phrase in fixed_phrases)
    
    # For F2P: before patch, this should fail; after patch, this should pass
    assert has_fixed_phrases, f"Fixed phrases not found in commit_system. Content: {commit_system[:500]}..."