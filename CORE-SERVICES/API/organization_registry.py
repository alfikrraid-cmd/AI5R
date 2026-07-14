from __future__ import annotations

from pathlib import Path
from typing import Any

from .company_manufacturing import retrieve_company_artifact
from .department_manufacturing import _departments_dir, retrieve_department_artifact
from .role_manufacturing import _roles_dir, retrieve_role_artifact

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def get_organization(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    """The Organization Registry: a read-only aggregation of existing artifacts.

    Manufactures nothing, persists nothing, modifies nothing. Artifacts
    remain the single source of truth; this only reads them back.
    """

    company = retrieve_company_artifact(product_name, root_path)

    departments_dir = _departments_dir(product_name, root_path)
    department_names = sorted(
        path.stem for path in departments_dir.glob("*.json")
    ) if departments_dir.exists() else []
    departments = [
        retrieve_department_artifact(product_name, name, root_path)
        for name in department_names
    ]

    roles_dir = _roles_dir(product_name, root_path)
    role_names = sorted(
        path.stem for path in roles_dir.glob("*.json")
    ) if roles_dir.exists() else []
    roles = [retrieve_role_artifact(product_name, name, root_path) for name in role_names]

    return {
        "company": company,
        "departments": departments,
        "roles": roles,
    }
