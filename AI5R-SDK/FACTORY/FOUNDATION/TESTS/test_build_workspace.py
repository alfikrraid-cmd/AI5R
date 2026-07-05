from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.build_workspace import BuildWorkspace


def test_build_workspace_creates_directories(tmp_path):
    workspace = BuildWorkspace(tmp_path / "BUILD-001")

    result = workspace.create()

    assert result["status"] == "WORKSPACE_CREATED"
    assert (tmp_path / "BUILD-001" / "INPUT").exists()
    assert (tmp_path / "BUILD-001" / "OUTPUT").exists()
    assert (tmp_path / "BUILD-001" / "REPORT").exists()
    assert (tmp_path / "BUILD-001" / "LOG").exists()
    assert (tmp_path / "BUILD-001" / "ARTIFACT").exists()
    assert (tmp_path / "BUILD-001" / "FREEZE").exists()


def test_build_workspace_returns_known_path(tmp_path):
    workspace = BuildWorkspace(tmp_path / "BUILD-001")
    workspace.create()

    assert workspace.path("OUTPUT") == tmp_path / "BUILD-001" / "OUTPUT"


def test_build_workspace_rejects_unknown_path(tmp_path):
    workspace = BuildWorkspace(tmp_path / "BUILD-001")

    try:
        workspace.path("UNKNOWN")
        assert False
    except ValueError as error:
        assert "Unknown workspace directory" in str(error)
