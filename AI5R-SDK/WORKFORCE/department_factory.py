from WORKFORCE.department import Department


class DepartmentFactory:
    def manufacture(
        self,
        department_name: str,
        organization_id: str,
        metadata: dict | None = None,
    ):
        if not department_name:
            raise ValueError("Department name is required")

        department = Department(
            department_name=department_name,
            organization_id=organization_id,
            metadata=metadata or {},
        )

        return {
            "status": "MANUFACTURED",
            "asset": department,
        }
