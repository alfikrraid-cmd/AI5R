from typing import Dict, List, Optional
from .department_object import DepartmentObject


class DepartmentRegistry:
    def __init__(self):
        self.departments: Dict[str, DepartmentObject] = {}

    def register(self, department: DepartmentObject) -> DepartmentObject:
        if department.department_id in self.departments:
            raise ValueError("Department already registered")

        if department.parent_department_id and department.parent_department_id not in self.departments:
            raise ValueError("Parent department not found")

        self.departments[department.department_id] = department
        return department

    def get(self, department_id: str) -> Optional[DepartmentObject]:
        return self.departments.get(department_id)

    def list_by_organization(self, organization_id: str) -> List[DepartmentObject]:
        return [
            dept for dept in self.departments.values()
            if dept.organization_id == organization_id
        ]

    def children_of(self, parent_department_id: str) -> List[DepartmentObject]:
        return [
            dept for dept in self.departments.values()
            if dept.parent_department_id == parent_department_id
        ]

    def hierarchy(self, organization_id: str) -> Dict:
        roots = [
            dept for dept in self.list_by_organization(organization_id)
            if dept.parent_department_id is None
        ]

        def build_node(dept: DepartmentObject):
            return {
                "department": dept.to_dict(),
                "children": [
                    build_node(child)
                    for child in self.children_of(dept.department_id)
                ],
            }

        return {
            "organization_id": organization_id,
            "departments": [build_node(root) for root in roots],
        }
