from IDENTITY.identity_object import IdentityObject


class IdentityEngine:

    def build(
        self,
        identity: IdentityObject,
    ):

        return {
            "status": "READY",
            "identity": identity,
            "profile": {
                "organization_id": identity.organization_id,
                "identity_name": identity.identity_name,
                "vision": identity.vision,
                "mission": identity.mission,
                "values": identity.values,
                "culture": identity.culture,
                "personality": identity.personality,
                "communication_style": identity.communication_style,
                "brand": identity.brand,
            },
        }
