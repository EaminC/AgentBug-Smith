import os
from unittest.mock import patch

import pytest

from strands.vended_memory_stores import BedrockKnowledgeBaseStore
from strands.vended_memory_stores.bedrock_knowledge_base.types import BedrockKnowledgeBaseConfig


class TestBedrockKnowledgeBaseStoreRegionResolution:
    def test_explicit_region_name_passed_to_boto3_client(self):
        with patch("boto3.client") as client_fn:
            store = BedrockKnowledgeBaseStore(
                config=BedrockKnowledgeBaseConfig(
                    knowledge_base_id="kb-1",
                    region_name="us-west-2",
                ),
                name="kb",
            )
            # The eager runtime client is constructed at init with region_name passed
            client_fn.assert_called_once_with("bedrock-agent-runtime", region_name="us-west-2")
            assert store._region == "us-west-2"

    def test_no_region_name_passes_none_to_boto3_client(self, tmp_path, monkeypatch):
        # Remove any AWS region environment variables and config to simulate no region hint
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-such-config"))

        with patch("boto3.client") as client_fn:
            store = BedrockKnowledgeBaseStore(
                config=BedrockKnowledgeBaseConfig(knowledge_base_id="kb-1"),
                name="kb",
            )
            # Should pass region_name=None explicitly so boto3 resolves region itself
            client_fn.assert_called_once_with("bedrock-agent-runtime", region_name=None)
            assert store._region is None

    def test_region_name_threads_to_lazy_clients(self):
        with patch("boto3.client") as client_fn:
            store = BedrockKnowledgeBaseStore(
                config=BedrockKnowledgeBaseConfig(
                    knowledge_base_id="kb-1",
                    data_source_type="CUSTOM",
                    data_source_id="ds-1",
                    region_name="eu-central-1",
                ),
                name="kb",
                writable=True,
            )
            # Eager runtime client constructed at init
            assert client_fn.call_count == 1
            # Lazy clients constructed on demand
            store._get_agent_client()
            store._get_s3_client()
            calls = {call.args[0]: call.kwargs["region_name"] for call in client_fn.call_args_list}
            assert calls == {
                "bedrock-agent-runtime": "eu-central-1",
                "bedrock-agent": "eu-central-1",
                "s3": "eu-central-1",
            }

    def test_no_region_name_threads_none_to_lazy_clients(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-such-config"))

        with patch("boto3.client") as client_fn:
            store = BedrockKnowledgeBaseStore(
                config=BedrockKnowledgeBaseConfig(
                    knowledge_base_id="kb-1",
                    data_source_type="CUSTOM",
                    data_source_id="ds-1",
                ),
                name="kb",
                writable=True,
            )
            store._get_agent_client()
            store._get_s3_client()
            calls = {call.args[0]: call.kwargs["region_name"] for call in client_fn.call_args_list}
            assert calls == {
                "bedrock-agent-runtime": None,
                "bedrock-agent": None,
                "s3": None,
            }


@pytest.mark.parametrize(
    "config_kwargs,expected_region",
    [
        ({}, None),
        ({"region_name": "us-east-1"}, "us-east-1"),
    ],
)
def test_store_init_and_region_propagation(config_kwargs, expected_region):
    with patch("boto3.client") as client_fn:
        store = BedrockKnowledgeBaseStore(
            config=BedrockKnowledgeBaseConfig(
                knowledge_base_id="kb-1",
                **config_kwargs,
            ),
            name="kb",
        )
        # The first client call is for runtime client
        client_fn.assert_called_with("bedrock-agent-runtime", region_name=expected_region)
        assert store._region == expected_region


def test_store_add_with_region_name_passes_region_to_lazy_clients():
    with patch("boto3.client") as client_fn:
        store = BedrockKnowledgeBaseStore(
            config=BedrockKnowledgeBaseConfig(
                knowledge_base_id="kb-1",
                data_source_type="CUSTOM",
                data_source_id="ds-1",
                region_name="us-west-1",
            ),
            name="kb",
            writable=True,
        )
        # Eager runtime client constructed at init
        assert client_fn.call_count == 1
        # Lazy clients constructed on demand during add
        store._get_agent_client()
        store._get_s3_client()
        calls = {call.args[0]: call.kwargs["region_name"] for call in client_fn.call_args_list}
        assert calls == {
            "bedrock-agent-runtime": "us-west-1",
            "bedrock-agent": "us-west-1",
            "s3": "us-west-1",
        }
