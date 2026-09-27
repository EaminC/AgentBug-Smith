import datetime
import os
from pathlib import Path

import pytest

from gpt_engineer.db import DB, DBs
from gpt_engineer.steps import archive


def test_archive_step_moves_folders_to_timestamped_directory(tmp_path, monkeypatch):
    """Test that archive step moves memory/workspace to archive with timestamp."""
    # Setup paths
    memory_path = tmp_path / "memory"
    workspace_path = tmp_path / "workspace" 
    archive_path = tmp_path / "archive"
    logs_path = tmp_path / "logs"
    preprompts_path = tmp_path / "preprompts"
    input_path = tmp_path / "input"
    
    # Create directories with content
    memory_path.mkdir(parents=True)
    workspace_path.mkdir(parents=True)
    archive_path.mkdir(parents=True)
    logs_path.mkdir(parents=True)
    preprompts_path.mkdir(parents=True)
    input_path.mkdir(parents=True)
    
    (memory_path / "file.txt").write_text("memory")
    (workspace_path / "file.txt").write_text("workspace")
    
    # Create DBs with archive field (6th argument)
    dbs = DBs(
        memory=DB(memory_path),
        logs=DB(logs_path),
        preprompts=DB(preprompts_path),
        input=DB(input_path),
        workspace=DB(workspace_path),
        archive=DB(archive_path)
    )
    
    # Freeze time for deterministic test
    frozen_time = datetime.datetime(2023, 6, 15, 14, 30, 45)
    
    class FrozenDatetime:
        @staticmethod
        def now():
            return frozen_time
    
    monkeypatch.setattr(datetime, "datetime", FrozenDatetime)
    
    # Execute archive step
    result = archive(None, dbs)
    
    # Assertions
    assert not os.path.exists(memory_path), "Memory path should be moved"
    assert not os.path.exists(workspace_path), "Workspace path should be moved"
    
    expected_timestamp = "20230615_143045"
    archived_memory = archive_path / expected_timestamp / "memory"
    archived_workspace = archive_path / expected_timestamp / "workspace"
    
    assert os.path.isdir(archived_memory), f"Archived memory should exist at {archived_memory}"
    assert os.path.isdir(archived_workspace), f"Archived workspace should exist at {archived_workspace}"
    assert (archived_memory / "file.txt").read_text() == "memory"
    assert (archived_workspace / "file.txt").read_text() == "workspace"
    assert result == []
