from DIGITAL_ORGANIZATION.organization_blueprint import OrganizationBlueprint
from DIGITAL_ORGANIZATION.organization_runtime import OrganizationRuntime
from DIGITAL_ORGANIZATION.department import Department


class BlueprintRuntime:

    def __init__(self):
        self._blueprints = {}

    def register(self, blueprint: OrganizationBlueprint):
        self._blueprints[blueprint.blueprint_id] = blueprint

        return {
            "status": "REGISTERED",
            "blueprint": blueprint,
        }

    def get(self, blueprint_id: str):
        return self._blueprints.get(blueprint_id)

    def deploy(self, blueprint_id: str, organization_name: str):
        blueprint = self.get(blueprint_id)

        if blueprint is None:
            return {
                "status": "NOT_FOUND",
                "organization": None,
            }

        runtime = OrganizationRuntime(name=organization_name)

        for department_name in blueprint.departments:
            runtime.add_department(
                Department(department_name)
            )

        blueprint.status = "DEPLOYED"

        return {
            "status": "DEPLOYED",
            "blueprint": blueprint,
            "organization_runtime": runtime,
        }

    def list_all(self):
        return list(self._blueprints.values())
