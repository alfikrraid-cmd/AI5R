from WORKFORCE.digital_employee import DigitalEmployee


class DigitalEmployeeFactory:

    def manufacture(
        self,
        employee_name: str,
        organization_id: str,
        identity_id: str,
        position_id: str,
        kernel_id: str,
        capability_ids: list | None = None,
        cognitive_function_ids: list | None = None,
        employment_type: str = "FULL_TIME",
        metadata: dict | None = None,
    ):

        employee = DigitalEmployee(
            employee_name=employee_name,
            organization_id=organization_id,
            identity_id=identity_id,
            position_id=position_id,
            kernel_id=kernel_id,
            capability_ids=capability_ids or [],
            cognitive_function_ids=cognitive_function_ids or [],
            employment_type=employment_type,
            metadata=metadata or {},
        )

        return {
            "status": "MANUFACTURED",
            "employee": employee,
        }
