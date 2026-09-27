import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import boto3
import pytest
from moto import mock_aws

from strands.session.s3_session_manager import S3SessionManager
from strands.types.content import ContentBlock
from strands.types.session import Session, SessionAgent, SessionMessage, SessionType


@pytest.fixture
def mocked_aws():
    with mock_aws():
        yield


@pytest.fixture(scope="function")
def s3_bucket(mocked_aws):
    s3_client = boto3.client("s3", region_name="us-west-2")
    s3_client.create_bucket(Bucket="test-session-bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-2"})
    return "test-session-bucket"


@pytest.fixture
def s3_manager(mocked_aws, s3_bucket):
    yield S3SessionManager(session_id="test", bucket=s3_bucket, prefix="sessions/", region_name="us-west-2")


@pytest.fixture
def sample_session():
    return Session(
        session_id="test-session-123",
        session_type=SessionType.AGENT,
    )


@pytest.fixture
def sample_agent():
    return SessionAgent(
        agent_id="test-agent-456",
        state={"key": "value"},
        conversation_manager_state={},
    )


@pytest.fixture
def sample_message():
    return SessionMessage.from_message(
        message={
            "role": "user",
            "content": [ContentBlock(text="test_message")],
        },
        index=0,
    )


def test_list_messages_parallel_order_preserved(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create multiple messages with known order
    messages = []
    for i in range(10):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"Message {i}")],
            },
            i,
        )
        messages.append(msg)
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # List messages and verify order is preserved
    listed_messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)

    assert len(listed_messages) == 10
    for i, msg in enumerate(listed_messages):
        assert msg.message["content"][0]["text"] == f"Message {i}"
        assert msg.message_id == i


def test_list_messages_with_limit_and_offset(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 10 messages
    for i in range(10):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Test limit
    limited = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id, limit=5)
    assert len(limited) == 5
    assert limited[0].message["content"][0]["text"] == "Msg 0"

    # Test offset
    offsetted = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id, offset=5)
    assert len(offsetted) == 5
    assert offsetted[0].message["content"][0]["text"] == "Msg 5"


def test_list_messages_handles_no_messages(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # No messages created
    result = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    assert result == []


def test_list_messages_parallel_fetch_performance(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 20 messages
    for i in range(20):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"Perf Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Measure time for list_messages
    start_time = time.time()
    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    duration = time.time() - start_time

    assert len(messages) == 20
    # Expect it to be reasonably fast (less than 2 seconds)
    assert duration < 2


def test_list_messages_parallel_fetch_order_consistency(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 15 messages
    for i in range(15):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"Consistent Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Call list_messages multiple times and verify order is consistent
    first_call = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    second_call = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)

    assert len(first_call) == len(second_call) == 15
    for m1, m2 in zip(first_call, second_call):
        assert m1.message_id == m2.message_id
        assert m1.message == m2.message


def test_list_messages_handles_missing_message(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 3 messages
    for i in range(3):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Manually delete one message object from S3 to simulate missing message
    key = s3_manager._get_message_path(sample_session.session_id, sample_agent.agent_id, 1)
    s3_manager.client.delete_object(Bucket=s3_manager.bucket, Key=key)

    # list_messages should skip missing message and not fail
    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    message_ids = [m.message_id for m in messages]

    assert 1 not in message_ids
    assert 0 in message_ids and 2 in message_ids


def test_list_messages_parallel_threadpool_used(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 5 messages
    for i in range(5):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"ThreadPool Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Patch _read_s3_object to record calls and simulate delay
    original_read = s3_manager._read_s3_object
    call_order = []

    def delayed_read(key):
        call_order.append(key)
        time.sleep(0.1)
        return original_read(key)

    s3_manager._read_s3_object = delayed_read

    # Call list_messages and verify that calls happen in parallel by timing
    start_time = time.time()
    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    duration = time.time() - start_time

    # Should be less than sum of all delays (0.1 * 5 = 0.5s), indicating parallelism
    assert duration < 0.5
    assert len(messages) == 5
    s3_manager._read_s3_object = original_read


def test_list_messages_single_message_no_threadpool(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create a single message
    msg = SessionMessage(
        {
            "role": "user",
            "content": [ContentBlock(text="Single Message")],
        },
        0,
    )
    s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Patch _read_s3_object to record calls
    original_read = s3_manager._read_s3_object
    call_count = 0

    def count_read(key):
        nonlocal call_count
        call_count += 1
        return original_read(key)

    s3_manager._read_s3_object = count_read

    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)

    # Should call _read_s3_object exactly once without threadpool overhead
    assert call_count == 1
    assert len(messages) == 1
    s3_manager._read_s3_object = original_read


def test_list_messages_with_offset_and_limit_parallel(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Create 10 messages
    for i in range(10):
        msg = SessionMessage(
            {
                "role": "user",
                "content": [ContentBlock(text=f"OffsetLimit Msg {i}")],
            },
            i,
        )
        s3_manager.create_message(sample_session.session_id, sample_agent.agent_id, msg)

    # Patch _read_s3_object to record keys read
    original_read = s3_manager._read_s3_object
    keys_read = []

    def record_read(key):
        keys_read.append(key)
        return original_read(key)

    s3_manager._read_s3_object = record_read

    # Use offset=3 and limit=4
    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id, limit=4, offset=3)

    # Should read exactly 4 messages starting from offset 3
    assert len(messages) == 4
    # Extract message_ids from messages
    message_ids = [m.message_id for m in messages]
    assert message_ids == [3, 4, 5, 6]

    # Keys read should correspond to those 4 messages
    expected_keys = [s3_manager._get_message_path(sample_session.session_id, sample_agent.agent_id, idx) for idx in message_ids]
    assert set(keys_read) == set(expected_keys)

    s3_manager._read_s3_object = original_read


def test_list_messages_handles_empty_message_keys(s3_manager: S3SessionManager, sample_session: Session, sample_agent: SessionAgent):
    s3_manager.create_session(sample_session)
    s3_manager.create_agent(sample_session.session_id, sample_agent)

    # Patch client.get_paginator to return empty contents
    original_get_paginator = s3_manager.client.get_paginator

    class EmptyPaginator:
        def paginate(self, **kwargs):
            yield {"Contents": []}

    s3_manager.client.get_paginator = lambda operation_name: EmptyPaginator()

    messages = s3_manager.list_messages(sample_session.session_id, sample_agent.agent_id)
    assert messages == []

    s3_manager.client.get_paginator = original_get_paginator
