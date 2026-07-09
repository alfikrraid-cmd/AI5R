from pathlib import Path

from FACTORY.ARTIFACTS.artifact_generator import ArtifactGenerator


def test_artifact_generator_materializes_templates(tmp_path):
    result = ArtifactGenerator().generate(
        workspace=str(tmp_path),
        pack_name="FASTAPI",
        artifacts=[
            {
                "template": "main.py.tpl",
                "path": "app/main.py",
            },
            {
                "template": "README.md.tpl",
                "path": "README.md",
            },
            {
                "template": "requirements.txt.tpl",
                "path": "requirements.txt",
            },
        ],
        context={
            "project_name": "Login API",
        },
    )

    assert result["status"] == "ARTIFACTS_GENERATED"
    assert result["count"] == 3
    assert (tmp_path / "app" / "main.py").exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "requirements.txt").exists()
    assert "Login API" in (tmp_path / "app" / "main.py").read_text(encoding="utf-8")
    assert "Login API" in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "fastapi" in (tmp_path / "requirements.txt").read_text(encoding="utf-8")
