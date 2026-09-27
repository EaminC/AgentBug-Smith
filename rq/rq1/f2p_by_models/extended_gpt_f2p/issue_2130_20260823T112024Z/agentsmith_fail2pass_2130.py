import warnings
import pytest
from strands.models.bedrock import BedrockModel


def test_default_model_warning_emitted_for_supported_regions(captured_warnings):
    # The fix now emits a UserWarning for default model usage even for supported regions.
    # We expect exactly one warning per call, and the warning message should mention default model usage.
    regions = ["us-west-2", "eu-west-2", "us-east-1", "eu-west-1", "us-gov-west-1"]
    for region in regions:
        captured_warnings.clear()
        model_id = BedrockModel._get_default_model_with_warning(region)
        assert model_id.endswith("claude-sonnet-4-20250514-v1:0")
        # There should be exactly one warning emitted per call
        assert len(captured_warnings) == 1
        warning_msg = str(captured_warnings[0].message)
        assert "default model" in warning_msg
        assert region in warning_msg or "default model" in warning_msg


def test_default_model_warning_emitted_for_unsupported_region(captured_warnings):
    # For unsupported regions, the warning about unsupported region and default model usage should be emitted.
    region = "ca-central-1"
    captured_warnings.clear()
    model_id = BedrockModel._get_default_model_with_warning(region)
    assert model_id.endswith("claude-sonnet-4-20250514-v1:0")
    # There should be at least one warning mentioning unsupported region
    region_warnings = [w for w in captured_warnings if "does not support" in str(w.message)]
    assert len(region_warnings) == 1
    assert "does not support" in str(region_warnings[0].message)
    # Also the default model usage warning should be present
    default_model_warnings = [w for w in captured_warnings if "default model" in str(w.message)]
    assert len(default_model_warnings) >= 1


def test_init_warns_on_unsupported_region(captured_warnings):
    # Initializing BedrockModel with unsupported region should emit a warning about unsupported region
    captured_warnings.clear()
    BedrockModel(region_name="ca-central-1")
    region_warnings = [w for w in captured_warnings if "does not support" in str(w.message)]
    assert len(region_warnings) == 1
    assert "does not support" in str(region_warnings[0].message)
    # Also the default model usage warning should be present
    default_model_warnings = [w for w in captured_warnings if "default model" in str(w.message)]
    assert len(default_model_warnings) >= 1


def test_init_no_warning_with_custom_model_id(captured_warnings):
    # Initializing BedrockModel with unsupported region but custom model_id should not emit unsupported region warning
    captured_warnings.clear()
    BedrockModel(region_name="ca-central-1", model_id="custom-model")
    region_warnings = [w for w in captured_warnings if "does not support" in str(w.message)]
    assert len(region_warnings) == 0
    # But default model warning should not be emitted either because custom model_id is specified
    default_model_warnings = [w for w in captured_warnings if "default model" in str(w.message)]
    assert len(default_model_warnings) == 0


def test_custom_model_id_not_overridden_by_region_formatting():
    # When a custom model_id is provided, the default model formatting should not override it
    custom_model_id = "custom.model.id"
    model = BedrockModel(model_id=custom_model_id)
    model_id = model.get_config().get("model_id")
    assert model_id == custom_model_id


def test_default_model_id_is_formatted_and_warns(captured_warnings):
    # Calling _get_default_model_with_warning returns a formatted default model id and emits warning
    captured_warnings.clear()
    model_id = BedrockModel._get_default_model_with_warning("us-east-1")
    assert model_id == "us.anthropic.claude-sonnet-4-20250514-v1:0"
    # There should be exactly one warning about default model usage
    default_model_warnings = [w for w in captured_warnings if "default model" in str(w.message)]
    assert len(default_model_warnings) == 1


@pytest.mark.parametrize("region", ["ap-southeast-1", "ap-northeast-1"])
def test_ap_region_prefix_converts_to_apac_and_warns(region, captured_warnings):
    # For AP regions, the prefix is converted to apac and default model warning is emitted
    captured_warnings.clear()
    model_id = BedrockModel._get_default_model_with_warning(region)
    assert model_id.startswith("apac.anthropic.claude-sonnet-4-20250514-v1")
    # There should be exactly one warning about default model usage
    default_model_warnings = [w for w in captured_warnings if "default model" in str(w.message)]
    assert len(default_model_warnings) == 1


def test_get_default_model_with_custom_model_id_no_warning(captured_warnings):
    # Providing a custom model_id disables warnings and returns the custom model_id
    captured_warnings.clear()
    custom_model_id = "custom-model"
    model_id = BedrockModel._get_default_model_with_warning("ca-central-1", {"model_id": custom_model_id})
    assert model_id == custom_model_id
    # No warnings should be emitted
    assert len(captured_warnings) == 0
