from POSITION.position_object import PositionObject


class PositionEngine:

    def build(
        self,
        position: PositionObject,
    ):

        return {
            "status": "READY",
            "position": position,
            "profile": {
                "organization_id": position.organization_id,
                "position_code": position.position_code,
                "position_name": position.position_name,
                "department": position.department,
                "reports_to": position.reports_to,
                "authority_level": position.authority_level,
                "approval_limit": position.approval_limit,
            },
        }
