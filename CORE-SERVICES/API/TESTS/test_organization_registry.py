import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.organization_registry import get_organization
from API.role_manufacturing import manufacture_role


def _seed_product(tmp_path, product_name):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")


def test_get_organization_returns_company_only_when_no_departments_or_roles(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")
    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )

    organization = get_organization("LTSA-BRAIN", root_path=tmp_path)

    assert organization["company"]["company"]["name"] == "CV Razzan Teknik Mandiri"
    assert organization["departments"] == []
    assert organization["roles"] == []


def test_get_organization_aggregates_departments_and_roles(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")
    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )
    manufacture_department(
        product_name="LTSA-BRAIN", department_name="Field Operations", root_path=tmp_path
    )
    manufacture_department(
        product_name="LTSA-BRAIN", department_name="Warehouse", root_path=tmp_path
    )
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        root_path=tmp_path,
    )
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Warehouse Lead",
        department_name="Warehouse",
        root_path=tmp_path,
    )

    organization = get_organization("LTSA-BRAIN", root_path=tmp_path)

    assert organization["company"]["company"]["name"] == "CV Razzan Teknik Mandiri"

    department_names = {d["department"]["name"] for d in organization["departments"]}
    assert department_names == {"Field Operations", "Warehouse"}

    role_names = {r["role"]["name"] for r in organization["roles"]}
    assert role_names == {"Field Technician", "Warehouse Lead"}


def test_get_organization_fails_without_company(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    try:
        get_organization("LTSA-BRAIN", root_path=tmp_path)
    except ValueError as exc:
        assert "no Company artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_get_organization_does_not_modify_artifacts(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")
    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )
    manufacture_department(
        product_name="LTSA-BRAIN", department_name="Field Operations", root_path=tmp_path
    )

    company_path = tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "company_artifact.json"
    department_path = (
        tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "DEPARTMENTS" / "Field Operations.json"
    )
    company_before = company_path.read_text(encoding="utf-8")
    department_before = department_path.read_text(encoding="utf-8")

    get_organization("LTSA-BRAIN", root_path=tmp_path)

    assert company_path.read_text(encoding="utf-8") == company_before
    assert department_path.read_text(encoding="utf-8") == department_before
