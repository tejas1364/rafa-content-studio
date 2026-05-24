from pathlib import Path


def test_github_actions_ci_runs_pytest():
    workflow = Path(".github/workflows/ci.yml")

    assert workflow.exists()
    text = workflow.read_text()
    assert "uv run --extra dev pytest -q" in text
    assert "python-version: '3.12'" in text
