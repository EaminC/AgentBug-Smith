import pytest
import aider.models
import openai


def find_model_class_with_configure():
    # Find the model class in aider.models that has configure_model_settings method
    for attr_name in dir(aider.models):
        attr = getattr(aider.models, attr_name)
        if isinstance(attr, type):
            if hasattr(attr, "configure_model_settings"):
                return attr
    return None


@pytest.mark.parametrize("model_name", [
    "azure/o1-preview-2024-09-12",
    "azure/o1-preview-2024-08-01",
    "azure/o1-preview-2023-12-31",
])
def test_o1_date_stamped_models_do_not_use_system_role(model_name):
    """
    Test that for date-stamped o1 models, the system prompt is disabled,
    so no message with role 'system' is included, preventing BadRequestError.
    """

    model_class = find_model_class_with_configure()
    assert model_class is not None

    instance = model_class(model_name)
    instance.configure_model_settings(model_name)

    # Patch openai.chat.completions.create to a dummy function that returns a dummy response
    def dummy_create(*args, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Dummy response"
                    }
                }
            ]
        }

    openai.chat.completions.create = dummy_create

    # Compose messages depending on use_system_prompt flag
    messages = []
    if instance.use_system_prompt:
        messages.append({"role": "system", "content": "System prompt"})
    messages.append({"role": "user", "content": "Hello"})

    # For date-stamped o1 models, system prompt should be disabled
    if "o1-" in model_name:
        assert not any(m["role"] == "system" for m in messages), \
            "System role message should not be included for date-stamped o1 models"
    else:
        # For other models, system prompt may be included
        pass


def test_o1_preview_date_stamped_model_configuration():
    """
    Test that the model settings for a date-stamped o1-preview model are configured correctly,
    specifically that use_system_prompt is False, use_temperature is False, and streaming is False.
    """

    model_class = find_model_class_with_configure()
    assert model_class is not None

    model_name = "azure/o1-preview-2024-09-12"
    instance = model_class(model_name)
    instance.configure_model_settings(model_name)

    # Check that the flags are set as expected for date-stamped o1 models
    assert instance.use_system_prompt is False, "use_system_prompt should be False for date-stamped o1 models"
    assert instance.use_temperature is False, "use_temperature should be False for date-stamped o1 models"
    assert instance.streaming is False, "streaming should be False for date-stamped o1 models"
