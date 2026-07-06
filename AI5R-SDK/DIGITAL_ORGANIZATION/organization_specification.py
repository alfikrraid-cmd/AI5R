from CORE.SPECIFICATION import Specification


class OrganizationSpecification(Specification):

    def __init__(
        self,
        organization_name: str,
        industry: str,
        departments: list[str],
        positions: list[str],
        capabilities: list[str],
        workflows: list[str] | None = None,
        version: str = "1.0.0",
        metadata: dict | None = None,
    ):
        super().__init__(
            specification_type="ORGANIZATION",
            specification_name=organization_name,
            version=version,
            metadata={
                "industry": industry,
                "departments": departments,
                "positions": positions,
                "capabilities": capabilities,
                "workflows": workflows or [],
                **(metadata or {}),
            },
        )
