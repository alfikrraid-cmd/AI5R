from CORE import UniversalFactory
from DIGITAL_ORGANIZATION.organization_runtime import OrganizationRuntime
from DIGITAL_ORGANIZATION.department import Department


class OrganizationFactory:

    def __init__(self):
        self.universal_factory = UniversalFactory()

    def manufacture(self, specification):

        manufactured = self.universal_factory.manufacture(specification)

        if manufactured["status"] != "MANUFACTURED":
            return {
                "status": "REJECTED",
                "reason": manufactured.get("reason"),
                "artifact": None,
                "organization_runtime": None,
            }

        artifact = manufactured["artifact"]

        organization_runtime = OrganizationRuntime(
            name=specification.specification_name,
        )

        for department_name in specification.metadata.get("departments", []):
            organization_runtime.add_department(
                Department(department_name)
            )

        return {
            "status": "MANUFACTURED",
            "artifact": artifact,
            "organization_runtime": organization_runtime,
            "specification": specification,
        }
