from pathlib import Path

from FACTORY.EXECUTION.build_validator import BuildValidator


def test_build_validator_accepts_complete_workspace(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").touch()
    (tmp_path / "README.md").touch()
    (tmp_path / "requirements.txt").touch()

    result = BuildValidator().validate(
        workspace=str(tmp_path),
        required_files=[
            "app/main.py",
            "README.md",
            "requirements.txt",
        ],
    )

    assert result["status"] == "BUILD_VALID"
    assert result["missing_files"] == []


def test_build_validator_reports_missing_files(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").touch()

    result = BuildValidator().validate(
        workspace=str(tmp_path),
        required_files=[
            "app/main.py",
            "README.md",
            "requirements.txt",
        ],
    )

    assert result["status"] == "BUILD_INVALID"
    assert "README.md" in result["missing_files"]
    assert "requirements.txt" in result["missing_files"]
