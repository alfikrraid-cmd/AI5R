import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ORGANIZATION.organization_worker import OrganizationWorker
from ORGANIZATION.organization_worker_registry import OrganizationWorkerRegistry


def test_organization_worker_registry():
    registry = OrganizationWorkerRegistry()

    org_id = "ORG-001"
    dept_id = "DEPT-ENG-001"

    worker = OrganizationWorker(
        organization_id=org_id,
        department_id=dept_id,
        worker_code="ENG-WORKER-001",
        worker_name="Engineering Worker",
        worker_type="AI_WORKER",
        capabilities={
            "code_generation": True,
            "architecture_review": True,
        },
    )

    registry.register(worker)

    assert registry.get(worker.worker_id).worker_code == "ENG-WORKER-001"
    assert len(registry.list_by_organization(org_id)) == 1
    assert len(registry.list_by_department(dept_id)) == 1
    assert registry.find_by_capability("code_generation")[0].worker_name == "Engineering Worker"

    print("OR-004 Organization Worker Registry OK")


if __name__ == "__main__":
    test_organization_worker_registry()
