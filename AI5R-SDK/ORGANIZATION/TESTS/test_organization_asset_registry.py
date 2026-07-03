import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ORGANIZATION.organization_asset import OrganizationAsset
from ORGANIZATION.organization_asset_registry import OrganizationAssetRegistry


def test_organization_asset_registry():
    registry = OrganizationAssetRegistry()

    org_id = "ORG-001"
    dept_id = "DEPT-ENG-001"
    worker_id = "WORKER-ENG-001"

    asset = OrganizationAsset(
        organization_id=org_id,
        department_id=dept_id,
        owner_worker_id=worker_id,
        asset_code="ASSET-DB-001",
        asset_name="LTSA Brain Database",
        asset_type="DATABASE",
        metadata={
            "engine": "postgresql",
            "schema": "public",
            "criticality": "high",
        },
    )

    registry.register(asset)

    assert registry.get(asset.asset_id).asset_code == "ASSET-DB-001"
    assert len(registry.list_by_organization(org_id)) == 1
    assert len(registry.list_by_department(dept_id)) == 1
    assert len(registry.list_by_owner_worker(worker_id)) == 1
    assert registry.find_by_type("DATABASE")[0].asset_name == "LTSA Brain Database"

    print("OR-005 Organization Asset Registry OK")


if __name__ == "__main__":
    test_organization_asset_registry()
