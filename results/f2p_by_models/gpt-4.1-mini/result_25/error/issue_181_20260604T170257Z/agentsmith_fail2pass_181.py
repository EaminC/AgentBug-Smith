import pytest
from mle.workflow import report
import os

def test_report_requires_token(monkeypatch):
    """
    This test verifies that the report function correctly requires and uses the github_token parameter.
    The buggy code ignores the passed github_token and always calls ask_github_token(),
    which causes unexpected behavior when token is None.
    The fixed code uses the passed token if available.

    We test by passing a dummy token and verifying it is used (mock ask_github_token to raise if called).
    """

    # Patch ask_github_token to raise if called, so we detect if the buggy code calls it unexpectedly.
    def fail_ask_github_token():
        raise RuntimeError("ask_github_token() should not be called when token is provided")

    monkeypatch.setattr(report, "ask_github_token", fail_ask_github_token)

    # Prepare dummy parameters
    work_dir = os.getcwd()
    github_repo = "MLSysOps/MLE-agent"
    github_username = "dummyuser"
    github_token = "dummy_token_123"
    okr_str = "Test OKR"

    # Call report with github_token provided
    # On buggy code, this will call ask_github_token() and raise RuntimeError
    # On fixed code, it will use the passed token and not raise
    try:
        report.report(work_dir, github_repo, github_username, github_token=github_token, okr_str=okr_str)
    except RuntimeError as e:
        pytest.fail(f"Bug detected: ask_github_token() was called despite providing github_token: {e}")

    # If no exception, test passes (fixed behavior)

@pytest.mark.asyncio
async def test_gen_report_api_accepts_token(monkeypatch):
    """
    This test verifies that the gen_report function in mle.server.app accepts the token parameter
    and passes it down to the workflow.report.report function.

    We patch workflow.report.report to record the token passed.
    The buggy code does not pass token, so the patched function will receive None.
    The fixed code passes the token argument.

    This test requires importing the real gen_report function and calling it with a ReportRequest including token.
    """

    from mle.server import app

    # Container to capture token argument passed to report.report
    captured = {}

    def fake_report(work_dir, github_repo, github_username, github_token=None, okr_str=None, model=None):
        captured["token"] = github_token
        return "fake_report_result"

    monkeypatch.setattr(report, "report", fake_report)

    # Create a ReportRequest with token
    rr = app.ReportRequest(
        repo="MLSysOps/MLE-agent",
        username="dummyuser",
        token="my_test_token_456",
        okr="Test OKR"
    )

    # Call gen_report synchronously
    result = app.gen_report(rr)

    # Check that the token passed to report.report matches the one in ReportRequest
    assert captured.get("token") == rr.token, "Token was not passed correctly to report.report"

    # Also check result is as expected from fake_report
    assert result == "fake_report_result"

@pytest.mark.asyncio
async def test_gen_report_async_api_accepts_token(monkeypatch):
    """
    Similar to test_gen_report_api_accepts_token but for the async version gen_report_async.
    """

    from mle.server import app

    captured = {}

    def fake_report(work_dir, github_repo, github_username, github_token=None, okr_str=None, model=None):
        captured["token"] = github_token
        return "fake_report_result"

    monkeypatch.setattr(report, "report", fake_report)

    rr = app.ReportRequest(
        repo="MLSysOps/MLE-agent",
        username="dummyuser",
        token="async_test_token_789",
        okr="Test OKR"
    )

    result = await app.gen_report_async(rr)

    assert captured.get("token") == rr.token, "Token was not passed correctly to report.report in async"
    assert result == "fake_report_result"