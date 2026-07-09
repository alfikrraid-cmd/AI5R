from pathlib import Path

from FACTORY.RUNTIME import FactoryRuntime


def test_factory_runtime_executes_complete_pipeline(tmp_path):

    plan = {
        "product_name": "Login API",
        "artifacts": [
            "app/main.py",
            "app/routers/auth.py",
            "app/schemas.py",
            "README.md",
            "requirements.txt",
            "openapi.json",
        ],
    }

    result = FactoryRuntime().run(
        plan,
        output_root=str(tmp_path),
    )

    assert result["status"] == "FACTORY_COMPLETED"

    assert result["execution"].status == "EXECUTED"

    assert result["validation"]["status"] == "BUILD_VALID"

    assert Path(
        result["archive"]["zip_path"]
    ).exists()
