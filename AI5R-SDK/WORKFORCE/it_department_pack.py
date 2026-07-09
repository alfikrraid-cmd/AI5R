from WORKFORCE.department_factory import DepartmentFactory
from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.organization import Organization


class ITDepartmentPack:
    DEFAULT_POSITIONS = [
        ("AI CTO", "CTO", ["TECH_STRATEGY", "ARCHITECTURE"]),
        ("AI Project Manager", "PROJECT_MANAGER", ["SPRINT_PLANNING", "TASK_BREAKDOWN"]),
        ("AI Solution Architect", "SOLUTION_ARCHITECT", ["SYSTEM_DESIGN", "ARCHITECTURE"]),
        ("AI Backend Engineer", "BACKEND_ENGINEER", ["PYTHON", "API", "DATABASE"]),
        ("AI Frontend Engineer", "FRONTEND_ENGINEER", ["UI", "REACT"]),
        ("AI QA Engineer", "QA_ENGINEER", ["PYTEST", "QUALITY_ASSURANCE"]),
        ("AI DevOps Engineer", "DEVOPS_ENGINEER", ["CI_CD", "DEPLOYMENT"]),
        ("AI Security Engineer", "SECURITY_ENGINEER", ["SECURITY_REVIEW"]),
        ("AI Documentation Engineer", "DOCUMENTATION_ENGINEER", ["DOCUMENTATION"]),
    ]

    def manufacture(self, organization: Organization):
        department = DepartmentFactory().manufacture(
            department_name="IT",
            organization_id=organization.organization_id,
            metadata={
                "pack": "IT_DEPARTMENT_PACK",
            },
        )["asset"]

        organization.add_department(department.department_id)

        employees = []

        for employee_name, position_id, capability_ids in self.DEFAULT_POSITIONS:
            employee = DigitalEmployeeFactory().manufacture(
                employee_name=employee_name,
                organization_id=organization.organization_id,
                identity_id=f"ID-{position_id}",
                position_id=position_id,
                kernel_id="KERNEL-AI5R",
                capability_ids=capability_ids,
                metadata={
                    "department_id": department.department_id,
                    "department_name": department.department_name,
                },
            )["employee"]

            department.add_employee(employee.employee_id)
            organization.add_employee(employee.employee_id)
            employees.append(employee)

        return {
            "status": "MANUFACTURED",
            "organization": organization,
            "department": department,
            "employees": employees,
        }
