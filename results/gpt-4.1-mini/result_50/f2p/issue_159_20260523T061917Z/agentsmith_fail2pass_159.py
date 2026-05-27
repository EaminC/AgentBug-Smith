import json
import pytest

import mle.agents.advisor as advisor_module
import mle.utils.system as system_module


class DummyModel:
    def query(self, chat_history, response_format=None):
        # Simulate the model's response for dataset clarity check and suggestions
        last_user_message = chat_history[-1]["content"].lower()
        if "response format: yes / no" in last_user_message:
            # This is the clarity check prompt
            # Return "No" to simulate unclear/blur dataset name
            return "No"
        if "json output format" in last_user_message:
            # This is the dataset suggestion prompt
            suggestions = {
                "datasets": ["dataset1", "dataset2", "dataset3"],
                "reason": "Based on the user's dataset description, these datasets are relevant."
            }
            return json.dumps(suggestions)
        return "Yes"


class DummyConsole:
    def status(self, message):
        # Context manager dummy for console.status
        class DummyStatus:
            def __enter__(self_):
                return self_

            def __exit__(self_, exc_type, exc_val, exc_tb):
                pass

        return DummyStatus()


def test_clarify_dataset_blur_name(monkeypatch):
    """
    Test that when a blur dataset name is provided, the advisor suggests datasets.
    This fails on the buggy codebase with an AttributeError because the method 
    does not exist, and passes on the fixed codebase.
    """

    dummy_model = DummyModel()
    dummy_console = DummyConsole()

    # Patch print_in_box to avoid actual console output
    monkeypatch.setattr(system_module, "print_in_box", lambda *a, **k: None)

    # Patch questionary.select to simulate user selecting the first suggested dataset
    import questionary

    def dummy_select(prompt, choices):
        class DummySelect:
            def ask(self):
                return choices[0]

        return DummySelect()

    monkeypatch.setattr(questionary, "select", dummy_select)

    # Patch get_config to return a dummy config dict to avoid NoneType error in AdviseAgent.__init__
    monkeypatch.setattr(advisor_module, "get_config", lambda: {"search_key": "dummy"})

    # Instantiate the agent
    advisor = advisor_module.AdviseAgent(dummy_model, dummy_console)

    # Call clarify_dataset with a blur dataset name
    # On the buggy codebase, this throws an AttributeError resulting in exit code 1.
    result = advisor.clarify_dataset("blur-dataset")

    # On the fixed codebase, this validates the suggestion logic resulting in exit code 0.
    assert result == "dataset1"

if __name__ == "__main__":
    pytest.main([__file__])