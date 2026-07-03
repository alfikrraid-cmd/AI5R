from typing import Dict, List, Optional
from .organization_policy import OrganizationPolicy


class OrganizationPolicyRegistry:
    def __init__(self):
        self.policies: Dict[str, OrganizationPolicy] = {}

    def register(self, policy: OrganizationPolicy) -> OrganizationPolicy:
        if policy.policy_id in self.policies:
            raise ValueError("Policy already registered")

        self.policies[policy.policy_id] = policy
        return policy

    def get(self, policy_id: str) -> Optional[OrganizationPolicy]:
        return self.policies.get(policy_id)

    def list_by_organization(self, organization_id: str) -> List[OrganizationPolicy]:
        return [
            policy for policy in self.policies.values()
            if policy.organization_id == organization_id
        ]

    def list_by_department(self, department_id: str) -> List[OrganizationPolicy]:
        return [
            policy for policy in self.policies.values()
            if policy.department_id == department_id
        ]

    def effective_policies(
        self,
        organization_id: str,
        department_id: Optional[str] = None
    ) -> List[OrganizationPolicy]:
        org_policies = [
            policy for policy in self.list_by_organization(organization_id)
            if policy.department_id is None
        ]

        dept_policies = []
        if department_id:
            dept_policies = self.list_by_department(department_id)

        return org_policies + dept_policies

    def evaluate(
        self,
        organization_id: str,
        department_id: Optional[str],
        rule_key: str
    ):
        policies = self.effective_policies(organization_id, department_id)

        result = None
        for policy in policies:
            if rule_key in policy.rules:
                result = policy.rules[rule_key]

        return result
