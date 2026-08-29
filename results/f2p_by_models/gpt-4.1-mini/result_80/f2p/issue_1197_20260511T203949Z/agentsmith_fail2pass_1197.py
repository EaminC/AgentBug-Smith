import os
import pytest

from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.paths import memory_path
from gpt_engineer.core.default.steps import salvage_correct_hunks
from gpt_engineer.core.files_dict import FilesDict
from langchain_core.messages import AIMessage

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
memory = DiskMemory(memory_path("."))


def get_file_content(file_path: str) -> str:
    with open(
        os.path.join(TEST_DIR, "core", "improve_function_test_cases", file_path), "r"
    ) as f:
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
    """
    This test triggers the bug described in issue 1197:
    When applying diffs that add a new yaml config file (application-local.yml),
    the code fails with KeyError on 'src/main/resources/application-stage.yml'.

    After applying the fix patch, this test should pass without exceptions.
    """
    # Setup initial files dict with only application.yml content
    files = FilesDict(
        {"src/main/resources/application.yml": get_file_content("zbf_yml_missing_code")}
    )
    # Run salvage_correct_hunks with the chat containing diffs that add application-local.yml
    updated_files, errors = salvage_correct_hunks(
        message_builder("zbf_yml_missing_chat"), files, memory
    )

    # The test expects no errors and that the new file application-local.yml is present
    assert errors == []
    assert "src/main/resources/application-local.yml" in updated_files
    # The original application.yml should still be present and updated_files should be a dict
    assert "src/main/resources/application.yml" in updated_files
    assert isinstance(updated_files, dict)

    # Check that the content of the new local yaml contains H2 DB config (a known string)
    local_yaml_content = updated_files["src/main/resources/application-local.yml"]
    assert "jdbc:h2:mem:testdb" in local_yaml_content
    assert "spring:" in local_yaml_content

    # Check that the stage yaml still contains the postgres url
    stage_yaml_content = updated_files["src/main/resources/application.yml"]
    assert "jdbc:postgresql" in stage_yaml_content
    assert "spring:" in stage_yaml_content


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
