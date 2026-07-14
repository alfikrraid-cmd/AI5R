from __future__ import annotations

from pathlib import Path
from typing import Any

from .organization_registry import get_organization

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def get_organization_dashboard(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    """The Organization Home Dashboard: a read-only presentation of the
    Organization Registry. Manufactures nothing, persists nothing,
    modifies nothing. Organization Registry is the single datasource.
    """

    organization = get_organization(product_name, root_path)

    company = organization["company"]
    departments = organization["departments"]
    roles = organization["roles"]

    role_counts: dict[str, int] = {}
    for role in roles:
        department_name = role["relationships"]["department"]
        role_counts[department_name] = role_counts.get(department_name, 0) + 1

    return {
        "organization": {
            "company_name": company["company"]["name"],
            "status": company["company"]["status"],
        },
        "business_domains": [department["department"]["name"] for department in departments],
        "summary": {
            "total_departments": len(departments),
            "total_roles": len(roles),
        },
        "departments": [
            {
                "name": department["department"]["name"],
                "parent_department": department["relationships"]["parent_department"],
                "role_count": role_counts.get(department["department"]["name"], 0),
            }
            for department in departments
        ],
        "roles": [
            {
                "name": role["role"]["name"],
                "department": role["relationships"]["department"],
                "reports_to": role["relationships"]["reports_to_role"],
            }
            for role in roles
        ],
    }
