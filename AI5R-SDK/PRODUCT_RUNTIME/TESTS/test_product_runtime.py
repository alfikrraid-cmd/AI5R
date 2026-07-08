import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_RUNTIME import ProductRuntime


def test_product_runtime_start(tmp_path):
    runtime = ProductRuntime(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
            "Decision",
        ],
    )

    result = runtime.start(specification)

    assert result["status"] == "RUNNING"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert len(result["domains"]) == 4

    runtime_file = (
        tmp_path /
        "PRODUCTS" /
        "DIGITAL_EMPLOYEE" /
        "runtime_state.json"
    )

    assert runtime_file.exists()


def test_product_runtime_status(tmp_path):
    runtime = ProductRuntime(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=["Identity"],
    )

    runtime.start(specification)

    status = runtime.status("digital employee")

    assert status["status"] == "RUNNING"


def test_product_runtime_stop(tmp_path):
    runtime = ProductRuntime(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=["Identity"],
    )

    runtime.start(specification)

    stopped = runtime.stop("digital employee")

    assert stopped["status"] == "STOPPED"
    assert "stopped_at" in stopped


def test_product_runtime_runs_goal_through_runtime_pipeline(tmp_path):
    runtime = ProductRuntime(tmp_path)

    specification = ProductSpecification(
        product_name="UMKM OS",
        domains=["Marketing", "Sales"],
    )

    runtime.start(specification)

    result = runtime.run_goal(
        product_name="UMKM OS",
        goal="Create UMKM sales plan",
        employee_id="EMP-001",
    )

    assert result["status"] == "SUCCESS"
    assert result["product"] == "UMKM_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert result["execution_count"] >= 1
    assert result["memory_count"] >= 1


def test_product_runtime_loads_product_by_name(tmp_path):
    runtime = ProductRuntime(tmp_path)

    result = runtime.load("UMKM OS")

    assert result["status"] == "RUNNING"
    assert result["product"] == "UMKM_OS"

    status = runtime.status("UMKM OS")

    assert status["status"] == "RUNNING"
