from pathlib import Path

from FACTORY.EXECUTION.workspace_builder import WorkspaceBuilder


def test_workspace_builder_creates_workspace(tmp_path):

    result = WorkspaceBuilder().build(
        [
            "app/main.py",
            "app/auth.py",
            "README.md",
            "requirements.txt",
        ],
        output_root=str(tmp_path),
    )

    assert result["status"] == "WORKSPACE_CREATED"

    workspace = Path(result["workspace"])

    assert workspace.exists()

    assert (workspace / "app" / "main.py").exists()

    assert (workspace / "app" / "auth.py").exists()

    assert (workspace / "README.md").exists()

    assert (workspace / "requirements.txt").exists()
