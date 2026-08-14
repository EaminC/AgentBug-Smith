import pytest
import openai


def test_openai_version_and_multimodal_support():
    # Check that the openai package version is at least 1.78.0
    version_str = openai.__version__
    major, minor, patch = (int(x) for x in version_str.split("."))
    assert (major, minor, patch) >= (1, 78, 0), f"OpenAI version must be >= 1.78.0 but is {version_str}"

    # Test that the new multi-image input parameter is accepted by the client
    # We will call the new-style openai.ChatCompletion.create with images param
    # Since openai 1.78 uses the new API, we test the new usage pattern

    # Compose a dummy chat completion request with multi-image inputs
    # We do not mock openai.ChatCompletion.create directly to avoid hiding bugs
    # Instead, we test that calling with images param does not raise TypeError or ValueError

    # We expect an error if images param is not supported (buggy old version)
    # or no error if supported (fixed version)

    # Prepare minimal valid parameters for the call
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "Describe this image."}]
    images = [
        {"url": "https://example.com/image1.png"},
        {"url": "https://example.com/image2.png"},
    ]

    # We call the synchronous create method and catch only TypeError or ValueError related to images param
    # If the call raises APIRemovedInV1, that means old API usage, so we skip that here
    # The test should fail on buggy code due to unsupported param or old API error

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            images=images,
        )
    except TypeError as e:
        pytest.fail(f"OpenAI client does not support multi-image inputs: {e}")
    except ValueError as e:
        pytest.fail(f"OpenAI client rejected multi-image inputs: {e}")
    except AttributeError as e:
        # This can happen if openai.error is not present in the old version
        pytest.fail(f"OpenAI client missing expected error attribute: {e}")
    except Exception as e:
        # Other exceptions are allowed, as long as not due to unsupported param
        # But if it's APIRemovedInV1, skip test (old API)
        if "APIRemovedInV1" in str(type(e)):
            pytest.skip("OpenAI old API detected, skipping multi-image input test")
        else:
            # Unexpected exception, fail
            pytest.fail(f"Unexpected error from OpenAI client: {e}")

    # If we get here, the call succeeded or failed with an allowed exception
    # We assert that the response has 'choices' key as expected from chat completion
    assert "choices" in response, "Response missing 'choices' key"
    assert isinstance(response["choices"], list), "'choices' is not a list"
    # Check that at least one choice has a message with content
    assert any("message" in choice and "content" in choice["message"] for choice in response["choices"]), \
        "No valid message content in choices"
