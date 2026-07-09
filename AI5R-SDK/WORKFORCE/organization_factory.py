from WORKFORCE.organization import Organization


class OrganizationFactory:
    def manufacture(
        self,
        organization_name: str,
        metadata: dict | None = None,
    ):
        if not organization_name:
            raise ValueError("Organization name is required")

        organization = Organization(
            organization_name=organization_name,
            metadata=metadata or {},
        )

        return {
            "status": "MANUFACTURED",
            "asset": organization,
        }
