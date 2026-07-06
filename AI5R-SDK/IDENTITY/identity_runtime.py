from IDENTITY.identity_engine import IdentityEngine


class IdentityRuntime:

    def __init__(self):
        self.engine = IdentityEngine()
        self._identities = {}

    def register(self, identity):

        result = self.engine.build(identity)

        self._identities[identity.identity_id] = result

        return {
            "status": "REGISTERED",
            "identity_id": identity.identity_id,
        }

    def get(self, identity_id):
        return self._identities.get(identity_id)

    def list_all(self):
        return list(self._identities.values())

    def list_by_organization(self, organization_id):
        return [
            x
            for x in self._identities.values()
            if x["identity"].organization_id == organization_id
        ]

    def list_by_brand(self, brand):
        return [
            x
            for x in self._identities.values()
            if x["identity"].brand == brand
        ]
