from ROLE.role_object import RoleObject


class RoleEngine:

    def build(
        self,
        role: RoleObject,
    ):

        return {
            "status": "READY",
            "role": role,
            "profile": {
                "authority_level": role.authority_level,
                "reasoning_depth": role.reasoning_depth,
                "risk_weight": role.risk_weight,
                "mission_weight": role.mission_weight,
                "policy_weight": role.policy_weight,
                "knowledge_scope": role.knowledge_scope,
                "execution_permission": role.execution_permission,
                "response_style": role.response_style,
            },
        }
