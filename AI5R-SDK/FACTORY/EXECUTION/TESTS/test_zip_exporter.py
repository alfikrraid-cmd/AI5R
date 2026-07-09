from pathlib import Path
from zipfile import ZipFile

from FACTORY.EXECUTION.zip_exporter import ZipExporter


def test_zip_exporter_exports_workspace(tmp_path):
    workspace = tmp_path / "RUN-001"
    workspace.mkdir()

    (workspace / "README.md").write_text("# AI5R", encoding="utf-8")
    (workspace / "app").mkdir()
    (workspace / "app" / "main.py").write_text("print('ok')", encoding="utf-8")

    result = ZipExporter().export(
        workspace=str(workspace),
    )

    zip_path = Path(result["zip_path"])

    assert result["status"] == "ZIP_EXPORTED"
    assert result["file_count"] == 2
    assert zip_path.exists()

    with ZipFile(zip_path) as zip_file:
        names = zip_file.namelist()

    assert "README.md" in names
    assert "app/main.py" in names


def test_zip_exporter_rejects_missing_workspace(tmp_path):
    missing = tmp_path / "missing"

    try:
        ZipExporter().export(
            workspace=str(missing),
        )
    except ValueError as exc:
        assert "workspace does not exist" in str(exc)
    else:
        raise AssertionError("Expected missing workspace export to fail")
