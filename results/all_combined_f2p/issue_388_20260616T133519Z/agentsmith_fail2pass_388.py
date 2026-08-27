import datetime
import os
import pytest
from unittest.mock import MagicMock, patch

from gpt_engineer.db import DB, DBs
from gpt_engineer.steps import archive


def freeze_at(monkeypatch, time):
    datetime_mock = MagicMock(wraps=datetime.datetime)
    datetime_mock.now.return_value = time
    monkeypatch.setattr(datetime, "datetime", datetime_mock)


def setup_dbs(tmp_path, dir_names):
    directories = [tmp_path / name for name in dir_names]
    dbs = [DB(dir) for dir in directories]
    return DBs(*dbs)


def test_archive_moves_memory_and_workspace(tmp_path, monkeypatch):
    dbs = setup_dbs(
        tmp_path, ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    )
    
    dbs.memory["test_file"] = "test content"
    dbs.workspace["output.txt"] = "output content"
    
    freeze_at(monkeypatch, datetime.datetime(2020, 12, 25, 17, 5, 55))
    
    archive(None, dbs)
    
    assert not os.path.exists(tmp_path / "memory")
    assert not os.path.exists(tmp_path / "workspace")
    assert os.path.isdir(tmp_path / "archive" / "20201225_170555")
    assert os.path.isdir(tmp_path / "archive" / "20201225_170555" / "memory")
    assert os.path.isdir(tmp_path / "archive" / "20201225_170555" / "workspace")


def test_archive_multiple_runs(tmp_path, monkeypatch):
    dbs = setup_dbs(
        tmp_path, ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    )
    
    dbs.memory["test_file"] = "test content"
    dbs.workspace["output.txt"] = "output content"
    
    freeze_at(monkeypatch, datetime.datetime(2020, 12, 25, 17, 5, 55))
    archive(None, dbs)
    
    assert os.path.isdir(tmp_path / "archive" / "20201225_170555")
    
    dbs = setup_dbs(
        tmp_path, ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    )
    dbs.memory["test_file2"] = "test content 2"
    dbs.workspace["output2.txt"] = "output content 2"
    
    freeze_at(monkeypatch, datetime.datetime(2022, 8, 14, 8, 5, 12))
    archive(None, dbs)
    
    assert not os.path.exists(tmp_path / "memory")
    assert not os.path.exists(tmp_path / "workspace")
    assert os.path.isdir(tmp_path / "archive" / "20201225_170555")
    assert os.path.isdir(tmp_path / "archive" / "20220814_080512")


def test_DBs_has_archive_attribute(tmp_path):
    dir_names = ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    directories = [tmp_path / name for name in dir_names]
    
    dbs = [DB(dir) for dir in directories]
    dbs_instance = DBs(*dbs)
    
    assert hasattr(dbs_instance, "archive")
    assert isinstance(dbs_instance.archive, DB)


def test_DBs_initialization_with_six_arguments(tmp_path):
    dir_names = ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    directories = [tmp_path / name for name in dir_names]
    
    dbs = [DB(dir) for dir in directories]
    dbs_instance = DBs(*dbs)
    
    assert isinstance(dbs_instance.memory, DB)
    assert isinstance(dbs_instance.logs, DB)
    assert isinstance(dbs_instance.preprompts, DB)
    assert isinstance(dbs_instance.input, DB)
    assert isinstance(dbs_instance.workspace, DB)
    assert isinstance(dbs_instance.archive, DB)


def test_archive_preserves_other_directories(tmp_path, monkeypatch):
    dbs = setup_dbs(
        tmp_path, ["memory", "logs", "preprompts", "input", "workspace", "archive"]
    )
    
    dbs.memory["test_file"] = "test content"
    dbs.workspace["output.txt"] = "output content"
    dbs.input["prompt"] = "test prompt"
    
    freeze_at(monkeypatch, datetime.datetime(2020, 12, 25, 17, 5, 55))
    archive(None, dbs)
    
    assert os.path.exists(tmp_path / "input")
    assert os.path.exists(tmp_path / "preprompts")
    assert os.path.exists(tmp_path / "logs")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
