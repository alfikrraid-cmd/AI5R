from pathlib import Path

from FACTORY.ARTIFACTS.artifact_writer import ArtifactWriter


def test_artifact_writer_writes_file(tmp_path):
    result = ArtifactWriter().write(
        workspace=str(tmp_path),
        artifact_path="app/main.py",
        content="print('AI5R')",
    )

    target = Path(result["path"])

    assert result["status"] == "ARTIFACT_WRITTEN"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "print('AI5R')"


def test_artifact_writer_creates_nested_directories(tmp_path):
    ArtifactWriter().write(
        workspace=str(tmp_path),
        artifact_path="app/routers/auth.py",
        content="# auth router",
    )

    assert (tmp_path / "app" / "routers" / "auth.py").exists()
