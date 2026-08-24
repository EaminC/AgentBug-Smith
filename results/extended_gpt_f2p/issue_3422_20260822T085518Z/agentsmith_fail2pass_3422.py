import pytest

from strands.models.llamacpp import LlamaCppModel


def test_format_request_with_llamacpp_params() -> None:
    """Test request formatting with llama.cpp specific parameters."""
    model = LlamaCppModel(
        params={
            "temperature": 0.8,
            "max_tokens": 50,
            "repeat_penalty": 1.1,
            "top_k": 40,
            "min_p": 0.05,
            "grammar": "root ::= 'yes' | 'no'",
        }
    )

    messages = [
        {"role": "user", "content": [{"text": "Is the sky blue?"}]},
    ]

    request = model._format_request(messages)

    # Standard OpenAI params
    assert request["temperature"] == 0.8
    assert request["max_tokens"] == 50

    # Grammar and json_schema go directly in request for llama.cpp
    assert request["grammar"] == "root ::= 'yes' | 'no'"

    # Other llama.cpp specific params go directly in the request body (the server
    # reads them at the top level; there is no OpenAI SDK to flatten extra_body).
    assert "extra_body" not in request
    assert request["repeat_penalty"] == 1.1
    assert request["top_k"] == 40
    assert request["min_p"] == 0.05


def test_format_request_with_all_new_params() -> None:
    """Test request formatting with all new llama.cpp parameters."""
    model = LlamaCppModel(
        params={
            # OpenAI params
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
            "seed": 42,
            # All llama.cpp specific params
            "repeat_penalty": 1.1,
            "top_k": 40,
            "min_p": 0.05,
            "typical_p": 0.95,
            "tfs_z": 0.97,
            "top_a": 0.1,
            "mirostat": 2,
            "mirostat_lr": 0.1,
            "mirostat_ent": 5.0,
            "grammar": "root ::= answer",
            "json_schema": {"type": "object"},
            "penalty_last_n": 256,
            "n_probs": 5,
            "min_keep": 1,
            "ignore_eos": False,
            "logit_bias": {100: 5.0, 200: -5.0},
            "cache_prompt": True,
            "slot_id": 1,
            "samplers": ["top_k", "tfs_z", "typical_p"],
        }
    )

    messages = [{"role": "user", "content": [{"text": "Test"}]}]
    request = model._format_request(messages)

    # Check OpenAI params are in root
    assert request["temperature"] == 0.7
    assert request["max_tokens"] == 100
    assert request["top_p"] == 0.9
    assert request["seed"] == 42

    # Grammar and json_schema go directly in request for llama.cpp
    assert request["grammar"] == "root ::= answer"
    assert request["json_schema"] == {"type": "object"}

    # All other llama.cpp params go directly in the request body, not nested under
    # an OpenAI-SDK-only extra_body object.
    assert "extra_body" not in request
    assert request["repeat_penalty"] == 1.1
    assert request["top_k"] == 40
    assert request["min_p"] == 0.05
    assert request["typical_p"] == 0.95
    assert request["tfs_z"] == 0.97
    assert request["top_a"] == 0.1
    assert request["mirostat"] == 2
    assert request["mirostat_lr"] == 0.1
    assert request["mirostat_ent"] == 5.0
    assert request["penalty_last_n"] == 256
    assert request["n_probs"] == 5
    assert request["min_keep"] == 1
    assert request["ignore_eos"] is False
    assert request["logit_bias"] == {100: 5.0, 200: -5.0}
    assert request["cache_prompt"] is True
    assert request["slot_id"] == 1
    assert request["samplers"] == ["top_k", "tfs_z", "typical_p"]


def test_format_request_llamacpp_params_are_top_level_not_extra_body() -> None:
    """llama.cpp sampling params are placed at the top level of the request body,
    not under extra_body. Regression test for #3422.
    """
    model = LlamaCppModel(
        params={
            "top_k": 40,
            "repeat_penalty": 1.1,
            "mirostat": 2,
            "samplers": ["top_k", "min_p"],
        }
    )

    request = model._format_request([{"role": "user", "content": [{"text": "hi"}]}])

    assert "extra_body" not in request
    assert request["top_k"] == 40
    assert request["repeat_penalty"] == 1.1
    assert request["mirostat"] == 2
    assert request["samplers"] == ["top_k", "min_p"]
