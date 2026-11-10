import os
import pytest

from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.paths import memory_path
from gpt_engineer.core.default.steps import salvage_correct_hunks
from gpt_engineer.core.files_dict import FilesDict
from langchain_core.messages import AIMessage

TEST_DIR = os.path.join(os.path.dirname(__file__), "core", "improve_function_test_cases")
memory = DiskMemory(memory_path("."))


def get_file_content(file_path: str) -> str:
    with open(os.path.join(TEST_DIR, file_path), "r") as f:
        return f.read()


def message_builder(chat_path: str):
    chat_content = get_file_content(chat_path)
    json = {
        "lc": 1,
        "type": "constructor",
        "id": ["langchain", "schema", "messages", "AIMessage"],
        "kwargs": {
            "content": chat_content,
            "additional_kwargs": {},
            "response_metadata": {"finish_reason": "stop"},
            "name": None,
            "id": None,
            "example": False,
        },
    }
    return [AIMessage(**json["kwargs"])]


def test_fail2pass_zbf_yml_missing():
    # Load initial files dict with only application.yml (stage config)
    files = FilesDict(
        {"src/main/resources/application.yml": get_file_content("zbf_yml_missing_code")}
    )
    # Run salvage_correct_hunks with the chat containing diffs to add application-local.yml
    updated_files, errors = salvage_correct_hunks(
        message_builder("zbf_yml_missing_chat"), files, memory
    )
    # The bug caused a KeyError on 'src/main/resources/application-stage.yml' which is not present in files.
    # After fix, the function should complete without errors and add the missing local yaml file.
    # Assert no errors returned
    assert errors == []
    # Assert the new local yaml file was added
    assert "src/main/resources/application-local.yml" in updated_files
    # Assert the original application.yml content is preserved or updated
    assert "spring:" in updated_files["src/main/resources/application.yml"]
    # Assert the local yaml file content includes H2 datasource url (indicating correct patch applied)
    local_yaml = updated_files["src/main/resources/application-local.yml"]
    assert "jdbc:h2:mem:testdb" in local_yaml
    # Also check that the stage yaml still contains postgres url
    stage_yaml = updated_files["src/main/resources/application.yml"]
    assert "jdbc:postgresql" in stage_yaml


if __name__ == "__main__":
    pytest.main()
