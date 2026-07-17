import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import (
    manufacture_company,
    retrieve_company_artifact,
)


def _seed_product(tmp_path, product_name):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")


def test_manufacture_company_produces_and_publishes_artifact(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    result = manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )

    assert result["company_artifact"]["company"]["name"] == "CV Razzan Teknik Mandiri"
    assert result["company_artifact"]["company"]["status"] == "ACTIVE"
    assert result["company_artifact"]["relationships"]["product"] == "LTSA-BRAIN"

    artifact_path = tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "company_artifact.json"
    assert artifact_path.exists()


def test_manufacture_company_fails_without_owning_product(tmp_path):
    try:
        manufacture_company(
            product_name="NO-SUCH-PRODUCT",
            company_name="Anyone",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "owning Product does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manufacture_company_rejects_duplicate(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )

    try:
        manufacture_company(
            product_name="LTSA-BRAIN",
            company_name="CV Razzan Teknik Mandiri",
            root_path=tmp_path,
        )
    except ValueError as exc:
        assert "already manufactured" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_retrieve_company_artifact_reads_back_published_artifact(tmp_path):
    _seed_product(tmp_path, "LTSA-BRAIN")

    manufacture_company(
        product_name="LTSA-BRAIN",
        company_name="CV Razzan Teknik Mandiri",
        root_path=tmp_path,
    )

    artifact = retrieve_company_artifact("LTSA-BRAIN", root_path=tmp_path)

    assert artifact["company"]["name"] == "CV Razzan Teknik Mandiri"


def test_retrieve_company_artifact_missing_raises(tmp_path):
    try:
        retrieve_company_artifact("NO-SUCH-PRODUCT", root_path=tmp_path)
    except ValueError as exc:
        assert "no Company artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
