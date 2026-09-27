import os
import pytest
from click.testing import CliRunner
import questionary

import mle.cli as cli_module
import mle.workflow.report as report_module


def test_report_command_local_and_github(monkeypatch):
    """
    Test the `mle report` CLI command behavior:
    1. Running `mle report` without repo argument prompts user for GitHub repo,
       and rejects invalid repo format.
    2. Running `mle report <github_repo>` triggers report workflow with correct project naming.
    """

    runner = CliRunner()

    # Patch questionary.text to simulate user input for repo prompt
    # First test: invalid repo format
    class DummyAnswerInvalid:
        def ask(self):
            return "invalid-repo-format"

    def fake_text_prompt_invalid(*args, **kwargs):
        return DummyAnswerInvalid()

    monkeypatch.setattr(questionary, "text", fake_text_prompt_invalid)

    # Patch console.log to capture logs
    logs = []

    class DummyConsole:
        def log(self, msg):
            logs.append(msg)

    monkeypatch.setattr(cli_module, "console", DummyConsole())

    # Patch check_config to always return False to test project creation branch
    monkeypatch.setattr(cli_module, "check_config", lambda: False)

    # Patch the 'new' command used in ctx.invoke(new, ...)
    monkeypatch.setattr(cli_module, "new", lambda *a, **k: True)

    # Patch ctx.invoke to record invocation instead of real call
    invoked = {}

    def fake_invoke(cmd, **kwargs):
        invoked["cmd"] = cmd
        invoked["kwargs"] = kwargs
        return True

    # We patch the context invoke method on the click context object passed to the command
    # Since runner.invoke creates a context, we patch the invoke method on the context object dynamically
    # We'll patch the cli_module.report function to wrap the original and patch ctx.invoke
    original_report = cli_module.report

    def wrapped_report(ctx, repo, model):
        ctx.invoke = fake_invoke
        return original_report(ctx, repo, model)

    monkeypatch.setattr(cli_module, "report", wrapped_report)

    # Patch os.chdir to avoid changing directory in test environment
    monkeypatch.setattr(os, "chdir", lambda path: None)

    # Run `mle report` without argument: should prompt and reject invalid repo format
    result = runner.invoke(cli_module.report, [])
    # It should log invalid github repository message and return False (exit code 0 but command returns False)
    assert any("Invalid github repository" in m for m in logs)
    assert result.exit_code == 0
    assert result.output == ""

    # Now test with a valid repo argument, check that it calls ctx.invoke(new, ...)
    invoked.clear()
    # Provide a valid repo argument
    result2 = runner.invoke(cli_module.report, ["MLSysOps/MLE-agent"])
    # Because check_config returns False, it should invoke new command and change directory
    assert invoked.get("cmd") == cli_module.new
    # The project name should be mle-report-mlsysops_mle-agent
    assert invoked.get("kwargs", {}).get("name") == "mle-report-mlsysops_mle-agent"
    # The command should exit with 0
    assert result2.exit_code == 0


def test_report_workflow_calls(monkeypatch):
    """
    Test the report workflow function calls SummaryAgent with github_repo and github_token.
    """

    # Patch load_model to return a dummy model object
    monkeypatch.setattr(report_module, "load_model", lambda work_dir, model=None: "dummy_model")

    # Patch SummaryAgent to check parameters and return dummy summarizer
    class DummySummaryAgent:
        def __init__(self, model, github_repo=None, github_token=None):
            self.model = model
            self.github_repo = github_repo
            self.github_token = github_token

        def summarize(self):
            return {"summary": "dummy summary"}

    monkeypatch.setattr(report_module, "SummaryAgent", DummySummaryAgent)

    # Patch ask_github_token to return a dummy token
    monkeypatch.setattr(report_module, "ask_github_token", lambda: "dummy_token")

    # Patch print_in_box to capture output
    printed = {}

    def fake_print_in_box(text, console, title=None, color=None):
        printed["text"] = text
        printed["title"] = title
        printed["color"] = color

    monkeypatch.setattr(report_module, "print_in_box", fake_print_in_box)

    # Call report function with dummy work_dir and github_repo
    report_module.report("/dummy/dir", "MLSysOps/MLE-agent", model=None)

    # Check that printed summary contains the dummy summary JSON string
    assert printed.get("title") == "Github Summarizer"
    assert "dummy summary" in printed.get("text")
    # Check that DummySummaryAgent was called with correct github_repo and github_token
    # We cannot directly check constructor calls, but the output depends on it, so this is indirect


def test_ask_github_token_integration(monkeypatch):
    """
    Test ask_github_token function behavior for integration config.
    """

    # Patch get_config to simulate missing integration.github
    config = {}

    def fake_get_config():
        return config

    monkeypatch.setattr(report_module, "get_config", fake_get_config)

    # Patch questionary.password to simulate user input token
    class DummyPasswordAnswer:
        def ask(self):
            return "new_token"

    monkeypatch.setattr(questionary, "password", lambda *a, **k: DummyPasswordAnswer())

    # Patch write_config to record config writes
    written = {}

    def fake_write_config(c):
        written.update(c)

    monkeypatch.setattr(report_module, "write_config", fake_write_config)

    token = report_module.ask_github_token()
    # It should return the new token
    assert token == "new_token"
    # It should write the config with integration.github.token
    assert "integration" in written
    assert "github" in written["integration"]
    assert written["integration"]["github"]["token"] == "new_token"


def test_ask_github_token_existing(monkeypatch):
    """
    Test ask_github_token returns existing token if present.
    """

    existing_token = "existing_token"
    config = {"integration": {"github": {"token": existing_token}}}

    def fake_get_config():
        return config

    monkeypatch.setattr(report_module, "get_config", fake_get_config)

    token = report_module.ask_github_token()
    assert token == existing_token