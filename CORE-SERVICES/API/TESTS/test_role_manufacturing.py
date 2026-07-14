import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.role_manufacturing import (
    _would_create_cycle,
    manufacture_role,
    retrieve_role_artifact,
)


def _seed_product(tmp_path, product_name):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")


def _seed_department(
    tmp_path,
    product_name,
    department_name="Field Operations",
    company_name="CV Razzan Teknik Mandiri",
):
    _seed_product(tmp_path, product_name)
    manufacture_company(product_name=product_name, company_name=company_name, root_path=tmp_path)
    manufacture_department(
        product_name=product_name, department_name=department_name, root_path=tmp_path
    )


def test_manufacture_role_produces_and_publishes_artifact(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    result = manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        responsibilities="Perform maintenance tasks",
        goals="Zero unplanned downtime",
        permissions="Read work orders",
        root_path=tmp_path,
    )

    assert result["role_artifact"]["role"]["name"] == "Field Technician"
    assert result["role_artifact"]["relationships"]["department"] == "Field Operations"
    assert result["role_artifact"]["relationships"]["reports_to_role"] is None

    artifact_path = tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "ROLES" / "Field Technician.json"
    assert artifact_path.exists()


def test_manufacture_role_fails_without_department(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    try:
        manufacture_role(
            product_name="LTSA-BRAIN",
            role_name="Field Technician",
            department_name="Field Operations",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "no Department artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_role_rejects_duplicate(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    try:
        manufacture_role(
            product_name="LTSA-BRAIN",
            role_name="Field Technician",
            department_name="Field Operations",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "already manufactured" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_role_with_valid_reports_to(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Supervisor",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    result = manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        reports_to_role_name="Field Supervisor",
        root_path=tmp_path,
    )

    assert result["role_artifact"]["relationships"]["reports_to_role"] == "Field Supervisor"


def test_manufacture_role_fails_with_missing_reports_to(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    try:
        manufacture_role(
            product_name="LTSA-BRAIN",
            role_name="Field Technician",
            department_name="Field Operations",
            reports_to_role_name="Nonexistent",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "reports-to Role does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_role_fails_with_reports_to_in_different_department(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")
    manufacture_department(
        product_name="LTSA-BRAIN", department_name="Warehouse", root_path=tmp_path
    )

    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Warehouse Lead",
        department_name="Warehouse",
        root_path=tmp_path,
    )

    try:
        manufacture_role(
            product_name="LTSA-BRAIN",
            role_name="Field Technician",
            department_name="Field Operations",
            reports_to_role_name="Warehouse Lead",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "different Department" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_would_create_cycle_detects_circular_ancestry(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    manufacture_role(product_name="LTSA-BRAIN", role_name="A", department_name="Field Operations", root_path=tmp_path)
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="B",
        department_name="Field Operations",
        reports_to_role_name="A",
        root_path=tmp_path,
    )

    # A -> B already exists (B reports to A). Attempting to make A report to B
    # would close the loop: A -> B -> A.
    assert _would_create_cycle("LTSA-BRAIN", "A", "B", tmp_path) is True
    assert _would_create_cycle("LTSA-BRAIN", "C", "B", tmp_path) is False


def test_retrieve_role_artifact_reads_back_published_artifact(tmp_path):
    _seed_department(tmp_path, "LTSA-BRAIN")

    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    artifact = retrieve_role_artifact("LTSA-BRAIN", "Field Technician", root_path=tmp_path)

    assert artifact["role"]["name"] == "Field Technician"


def test_retrieve_role_artifact_missing_raises(tmp_path):
    try:
        retrieve_role_artifact("LTSA-BRAIN", "Nonexistent", root_path=tmp_path)
    except ValueError as exc:
        assert "no Role artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
