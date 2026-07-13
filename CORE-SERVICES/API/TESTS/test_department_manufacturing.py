import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import (
    _would_create_cycle,
    manufacture_department,
    retrieve_department_artifact,
)


def _seed_product(tmp_path, product_name):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")


def _seed_company(tmp_path, product_name, company_name="CV Razzan Teknik Mandiri"):
    _seed_product(tmp_path, product_name)
    manufacture_company(product_name=product_name, company_name=company_name, root_path=tmp_path)


def test_manufacture_department_produces_and_publishes_artifact(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    result = manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="Field Operations",
        responsibilities="Maintenance execution",
        root_path=tmp_path,
    )

    assert result["department_artifact"]["department"]["name"] == "Field Operations"
    assert (
        result["department_artifact"]["relationships"]["company"]
        == "CV Razzan Teknik Mandiri"
    )
    assert result["department_artifact"]["relationships"]["parent_department"] is None

    artifact_path = (
        tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "DEPARTMENTS" / "Field Operations.json"
    )
    assert artifact_path.exists()


def test_manufacture_department_fails_without_company(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    try:
        manufacture_department(
            product_name="LTSA-BRAIN",
            department_name="Field Operations",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "no Company artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_department_rejects_duplicate(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    try:
        manufacture_department(
            product_name="LTSA-BRAIN",
            department_name="Field Operations",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "already manufactured" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_child_department_with_valid_parent(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    result = manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="Maintenance Crew",
        parent_department_name="Field Operations",
        root_path=tmp_path,
    )

    assert result["department_artifact"]["relationships"]["parent_department"] == "Field Operations"


def test_manufacture_department_fails_with_missing_parent(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    try:
        manufacture_department(
            product_name="LTSA-BRAIN",
            department_name="Maintenance Crew",
            parent_department_name="Nonexistent",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "parent Department does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_would_create_cycle_detects_circular_ancestry(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    manufacture_department(product_name="LTSA-BRAIN", department_name="A", root_path=tmp_path)
    manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="B",
        parent_department_name="A",
        root_path=tmp_path,
    )

    # A -> B already exists (B's parent is A). Attempting to make A a child
    # of B would close the loop: A -> B -> A.
    assert _would_create_cycle("LTSA-BRAIN", "A", "B", tmp_path) is True
    assert _would_create_cycle("LTSA-BRAIN", "C", "B", tmp_path) is False


def test_retrieve_department_artifact_reads_back_published_artifact(tmp_path):
    _seed_company(tmp_path, "LTSA-BRAIN")

    manufacture_department(
        product_name="LTSA-BRAIN",
        department_name="Field Operations",
        root_path=tmp_path,
    )

    artifact = retrieve_department_artifact(
        "LTSA-BRAIN", "Field Operations", root_path=tmp_path
    )

    assert artifact["department"]["name"] == "Field Operations"


def test_retrieve_department_artifact_missing_raises(tmp_path):
    try:
        retrieve_department_artifact("LTSA-BRAIN", "Nonexistent", root_path=tmp_path)
    except ValueError as exc:
        assert "no Department artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
