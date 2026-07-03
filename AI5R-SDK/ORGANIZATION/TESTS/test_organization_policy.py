import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ORGANIZATION.organization_policy import OrganizationPolicy
from ORGANIZATION.organization_policy_registry import OrganizationPolicyRegistry


def test_organization_policy():
    registry = OrganizationPolicyRegistry()

    org_id = "ORG-001"
    dept_id = "DEPT-ENG-001"

    org_policy = OrganizationPolicy(
        organization_id=org_id,
        policy_code="ORG-COST-FIRST",
        policy_name="Organization Cost First Policy",
        rules={
            "cost_first": True,
            "llm_usage": "restricted",
            "sql_before_llm": True,
        },
    )

    dept_policy = OrganizationPolicy(
        organization_id=org_id,
        department_id=dept_id,
        policy_code="ENG-LLM-USAGE",
        policy_name="Engineering LLM Usage Policy",
        rules={
            "llm_usage": "allowed_with_audit",
        },
    )

    registry.register(org_policy)
    registry.register(dept_policy)

    effective = registry.effective_policies(org_id, dept_id)

    assert len(effective) == 2
    assert registry.evaluate(org_id, dept_id, "cost_first") is True
    assert registry.evaluate(org_id, dept_id, "sql_before_llm") is True
    assert registry.evaluate(org_id, dept_id, "llm_usage") == "allowed_with_audit"

    print("OR-003 Organization Policy OK")


if __name__ == "__main__":
    test_organization_policy()
