import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.organization_dashboard import get_organization_dashboard
from API.role_manufacturing import manufacture_role


def _seed_product(tmp_path, product_name):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")


def test_dashboard_shows_organization_header_with_no_departments_or_roles(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")
    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )

    dashboard = get_organization_dashboard("LTSA-BRAIN", root_path=tmp_path)

    assert dashboard["organization"]["company_name"] == "CV Razzan Teknik Mandiri"
    assert dashboard["organization"]["status"] == "ACTIVE"
    assert dashboard["business_domains"] == []
    assert dashboard["summary"] == {"total_departments": 0, "total_roles": 0}
    assert dashboard["departments"] == []
    assert dashboard["roles"] == []


def test_dashboard_aggregates_business_domains_and_summary(tmp_path):
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
        product_name="LTSA-BRAIN",
        department_name="Maintenance Crew",
        parent_department_name="Field Operations",
        root_path=tmp_path,
    )
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Supervisor",
        department_name="Field Operations",
        root_path=tmp_path,
    )
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Field Technician",
        department_name="Field Operations",
        reports_to_role_name="Field Supervisor",
        root_path=tmp_path,
    )

    dashboard = get_organization_dashboard("LTSA-BRAIN", root_path=tmp_path)

    assert set(dashboard["business_domains"]) == {"Field Operations", "Maintenance Crew"}
    assert dashboard["summary"] == {"total_departments": 2, "total_roles": 2}

    departments_by_name = {d["name"]: d for d in dashboard["departments"]}
    assert departments_by_name["Field Operations"]["parent_department"] is None
    assert departments_by_name["Field Operations"]["role_count"] == 2
    assert departments_by_name["Maintenance Crew"]["parent_department"] == "Field Operations"
    assert departments_by_name["Maintenance Crew"]["role_count"] == 0

    roles_by_name = {r["name"]: r for r in dashboard["roles"]}
    assert roles_by_name["Field Supervisor"]["department"] == "Field Operations"
    assert roles_by_name["Field Supervisor"]["reports_to"] is None
    assert roles_by_name["Field Technician"]["reports_to"] == "Field Supervisor"


def test_dashboard_fails_without_company(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    try:
        get_organization_dashboard("LTSA-BRAIN", root_path=tmp_path)
    except ValueError as exc:
        assert "no Company artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_dashboard_does_not_modify_artifacts(tmp_path):
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

    get_organization_dashboard("LTSA-BRAIN", root_path=tmp_path)

    assert company_path.read_text(encoding="utf-8") == company_before
    assert department_path.read_text(encoding="utf-8") == department_before
