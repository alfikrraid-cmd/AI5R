from ROLE.role_engine import RoleEngine


class RoleRuntime:

    def __init__(self):
        self.engine = RoleEngine()
        self._roles = {}

    def register(self, role):

        result = self.engine.build(role)

        self._roles[role.role_id] = result

        return {
            "status": "REGISTERED",
            "role_id": role.role_id,
        }

    def get(self, role_id):
        return self._roles.get(role_id)

    def list_all(self):
        return list(self._roles.values())
