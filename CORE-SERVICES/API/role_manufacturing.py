from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from MANUFACTURING import ManufacturingOrder
from MANUFACTURING.role_recipe_registration import register_role_manufacturing
from MANUFACTURING_CENTER.manufacturing_result import ManufacturingResult
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus

from .department_manufacturing import retrieve_department_artifact
from .digital_factory_bootstrap import get_digital_factory

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def _roles_dir(product_name: str, root_path: Path | str) -> Path:
    return Path(root_path) / "PRODUCTS" / product_name / "ROLES"


def _role_artifact_path(product_name: str, role_name: str, root_path: Path | str) -> Path:
    return _roles_dir(product_name, root_path) / f"{role_name}.json"


def _load_role(product_name: str, role_name: str, root_path: Path | str) -> dict[str, Any] | None:
    path = _role_artifact_path(product_name, role_name, root_path)

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def _would_create_cycle(
    product_name: str,
    role_name: str,
    reports_to_role_name: str,
    root_path: Path | str,
) -> bool:
    current = reports_to_role_name
    visited: set[str] = set()

    while current:
        if current == role_name:
            return True

        if current in visited:
            break

        visited.add(current)

        parent_artifact = _load_role(product_name, current, root_path)

        if parent_artifact is None:
            break

        current = parent_artifact["relationships"].get("reports_to_role")

    return False


def manufacture_role(
    product_name: str,
    role_name: str,
    department_name: str,
    responsibilities: str = "",
    goals: str = "",
    permissions: str = "",
    reports_to_role_name: str | None = None,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    retrieve_department_artifact(product_name, department_name, root_path)

    if _role_artifact_path(product_name, role_name, root_path).exists():
        raise ValueError(f"Role already manufactured for product: {product_name}/{role_name}")

    if reports_to_role_name:
        parent_artifact = _load_role(product_name, reports_to_role_name, root_path)

        if parent_artifact is None:
            raise ValueError(f"reports-to Role does not exist: {reports_to_role_name}")

        if parent_artifact["relationships"]["department"] != department_name:
            raise ValueError("reports-to Role belongs to a different Department")

        if _would_create_cycle(product_name, role_name, reports_to_role_name, root_path):
            raise ValueError("reports-to Role assignment would create a circular ancestry")

    factory = get_digital_factory()
    register_role_manufacturing(factory)

    order = ManufacturingOrder(
        order_id=f"MO-ROLE-{uuid4().hex[:8].upper()}",
        product_name=product_name,
        product_type="ROLE",
        requested_by="AI5R",
        requirements={
            "role_name": role_name,
            "department_name": department_name,
            "reports_to_role_name": reports_to_role_name,
            "responsibilities": responsibilities,
            "goals": goals,
            "permissions": permissions,
        },
    )

    response = factory.manufacture_order(order)

    artifact = response.output["role_artifact"]

    published_path = publish_role_artifact(product_name, role_name, artifact, root_path)

    return {
        "status": str(response.status),
        "order_id": order.order_id,
        "artifact_path": str(published_path),
        "role_artifact": artifact,
    }


def publish_role_artifact(
    product_name: str,
    role_name: str,
    artifact: dict[str, Any],
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> Path:
    """The publishing mechanism: persists a Role Artifact the capability produced."""

    result = ManufacturingResult(
        manufacturing_id=f"MR-ROLE-{uuid4().hex[:8].upper()}",
        status=ManufacturingStatus.MANUFACTURING,
        started_at=datetime.now(UTC),
    )

    path = _role_artifact_path(product_name, role_name, root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    result.add_artifact(str(path))
    result.complete()

    return path


def retrieve_role_artifact(
    product_name: str,
    role_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    artifact = _load_role(product_name, role_name, root_path)

    if artifact is None:
        raise ValueError(f"no Role artifact found for product: {product_name}/{role_name}")

    return artifact
