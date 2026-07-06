import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_MANUFACTURING import ProductManufacturingController


def test_product_manufacturing_controller_manufactures_running_product(tmp_path):
    controller = ProductManufacturingController(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
            "Decision",
        ],
    )

    result = controller.manufacture(specification)

    assert result["status"] == "PRODUCT_RUNNING"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["runtime_status"] == "RUNNING"
    assert len(result["domains"]) == 4
    assert "artifact_path" in result


def test_product_manufacturing_controller_reports_status(tmp_path):
    controller = ProductManufacturingController(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=["Identity"],
    )

    controller.manufacture(specification)

    result = controller.status("digital employee")

    assert result["status"] == "PRODUCT_STATUS"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["runtime_status"] == "RUNNING"


def test_product_manufacturing_controller_stops_product(tmp_path):
    controller = ProductManufacturingController(tmp_path)

    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=["Identity"],
    )

    controller.manufacture(specification)

    result = controller.stop("digital employee")

    assert result["status"] == "PRODUCT_STOPPED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["runtime_status"] == "STOPPED"


def test_product_manufacturing_controller_returns_not_found(tmp_path):
    controller = ProductManufacturingController(tmp_path)

    result = controller.status("Unknown Product")

    assert result["status"] == "NOT_FOUND"
