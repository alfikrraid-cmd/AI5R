import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ORGANIZATION.multi_organization_runtime import (
    MultiOrganizationRuntime,
    OrganizationRuntimeContext,
)


def test_multi_organization_runtime():
    runtime = MultiOrganizationRuntime()

    org_a = "ORG-A"
    org_b = "ORG-B"

    context_a = OrganizationRuntimeContext(
        organization_id=org_a,
        runtime_name="Runtime A",
        department_id="DEPT-A-ENG",
        worker_id="WORKER-A-001",
        metadata={"tenant": "customer_a"},
    )

    context_b = OrganizationRuntimeContext(
        organization_id=org_b,
        runtime_name="Runtime B",
        department_id="DEPT-B-OPS",
        worker_id="WORKER-B-001",
        metadata={"tenant": "customer_b"},
    )

    runtime.register_context(context_a)
    runtime.register_context(context_b)

    runtime.activate_organization(org_a)

    assert runtime.active_organization_id == org_a
    assert len(runtime.list_contexts_by_organization(org_a)) == 1
    assert len(runtime.list_contexts_by_organization(org_b)) == 1

    isolated = runtime.isolate(
        org_a,
        {
            "mission": "generate_release",
            "asset": "database.sql",
        },
    )

    assert isolated["organization_id"] == org_a
    assert isolated["isolated"] is True
    assert isolated["payload"]["mission"] == "generate_release"

    print("OR-006 Multi-Organization Runtime OK")


if __name__ == "__main__":
    test_multi_organization_runtime()
