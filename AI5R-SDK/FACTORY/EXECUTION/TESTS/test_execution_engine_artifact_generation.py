from pathlib import Path

from FACTORY.EXECUTION import FactoryExecutionEngine


def test_execution_engine_generates_fastapi_artifacts(tmp_path):
    plan = {
        "product_name": "Login API",
        "product_type": "FASTAPI_SERVICE",
        "artifacts": [
            "app/main.py",
            "app/routers/auth.py",
            "app/schemas.py",
            "tests/test_login.py",
            "README.md",
            "requirements.txt",
            "openapi.json",
        ],
    }

    result = FactoryExecutionEngine().execute(
        plan,
        output_root=str(tmp_path),
    )

    workspace = Path(result.workspace["workspace"])

    assert result.status == "EXECUTED"
    assert result.metadata["generated_artifacts"] == 7
    assert (workspace / "app" / "main.py").exists()
    assert (workspace / "app" / "routers" / "auth.py").exists()
    assert (workspace / "app" / "schemas.py").exists()
    assert "FastAPI" in (workspace / "app" / "main.py").read_text(encoding="utf-8")
    assert "demo-token" in (workspace / "app" / "routers" / "auth.py").read_text(encoding="utf-8")
    assert "Login API" in (workspace / "README.md").read_text(encoding="utf-8")
