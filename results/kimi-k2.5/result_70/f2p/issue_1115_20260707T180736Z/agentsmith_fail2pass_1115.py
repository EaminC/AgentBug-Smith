import json
from unittest import mock

from gpt_engineer.applications.cli import learning
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.prompt import Prompt


def test_learning_prompt_is_json_serializable():
    """
    Test that Learning.prompt is a JSON string, not a Prompt object.
    
    Regression test for issue #1115: TypeError: Object of type Prompt is not JSON serializable
    """
    review = learning.Review(
        raw="y, n, y",
        ran=True,
        works=True,
        perfect=False,
        comments="Test comments",
    )
    memory = mock.Mock(spec=DiskMemory)
    memory.to_json.return_value = {"key": "value"}

    prompt_obj = Prompt("test prompt text", image_urls=["http://example.com/image.jpg"])

    result = learning.extract_learning(
        prompt_obj,
        "gpt-4",
        0.7,
        ("config",),
        memory,
        review,
    )

    # After the fix, prompt should be a JSON string, not a Prompt object
    assert isinstance(result.prompt, str), f"Expected str, got {type(result.prompt)}"
    
    # Verify it's valid JSON and contains expected data
    parsed = json.loads(result.prompt)
    assert parsed["text"] == "test prompt text"
    assert parsed["image_urls"] == ["http://example.com/image.jpg"]
