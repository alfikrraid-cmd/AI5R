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
from MANUFACTURING.department_recipe_registration import register_department_manufacturing
from MANUFACTURING_CENTER.manufacturing_result import ManufacturingResult
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus

from .company_manufacturing import retrieve_company_artifact
from .digital_factory_bootstrap import get_digital_factory

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def _departments_dir(product_name: str, root_path: Path | str) -> Path:
    return Path(root_path) / "PRODUCTS" / product_name / "DEPARTMENTS"


def _department_artifact_path(
    product_name: str, department_name: str, root_path: Path | str
) -> Path:
    return _departments_dir(product_name, root_path) / f"{department_name}.json"


def _load_department(
    product_name: str, department_name: str, root_path: Path | str
) -> dict[str, Any] | None:
    path = _department_artifact_path(product_name, department_name, root_path)

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def _would_create_cycle(
    product_name: str,
    department_name: str,
    parent_department_name: str,
    root_path: Path | str,
) -> bool:
    current = parent_department_name
    visited: set[str] = set()

    while current:
        if current == department_name:
            return True

        if current in visited:
            break

        visited.add(current)

        parent_artifact = _load_department(product_name, current, root_path)

        if parent_artifact is None:
            break

        current = parent_artifact["relationships"].get("parent_department")

    return False


def manufacture_department(
    product_name: str,
    department_name: str,
    responsibilities: str = "",
    parent_department_name: str | None = None,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    company_artifact = retrieve_company_artifact(product_name, root_path)
    company_name = company_artifact["company"]["name"]

    if _department_artifact_path(product_name, department_name, root_path).exists():
        raise ValueError(
            f"Department already manufactured for product: {product_name}/{department_name}"
        )

    if parent_department_name:
        parent_artifact = _load_department(product_name, parent_department_name, root_path)

        if parent_artifact is None:
            raise ValueError(f"parent Department does not exist: {parent_department_name}")

        if parent_artifact["relationships"]["company"] != company_name:
            raise ValueError("parent Department belongs to a different Company")

        if _would_create_cycle(product_name, department_name, parent_department_name, root_path):
            raise ValueError("parent Department assignment would create a circular ancestry")

    factory = get_digital_factory()
    register_department_manufacturing(factory)

    order = ManufacturingOrder(
        order_id=f"MO-DEPARTMENT-{uuid4().hex[:8].upper()}",
        product_name=product_name,
        product_type="DEPARTMENT",
        requested_by="AI5R",
        requirements={
            "department_name": department_name,
            "company_name": company_name,
            "parent_department_name": parent_department_name,
            "responsibilities": responsibilities,
        },
    )

    response = factory.manufacture_order(order)

    artifact = response.output["department_artifact"]

    published_path = publish_department_artifact(
        product_name, department_name, artifact, root_path
    )

    return {
        "status": str(response.status),
        "order_id": order.order_id,
        "artifact_path": str(published_path),
        "department_artifact": artifact,
    }


def publish_department_artifact(
    product_name: str,
    department_name: str,
    artifact: dict[str, Any],
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> Path:
    """The publishing mechanism: persists a Department Artifact the capability produced."""

    result = ManufacturingResult(
        manufacturing_id=f"MR-DEPARTMENT-{uuid4().hex[:8].upper()}",
        status=ManufacturingStatus.MANUFACTURING,
        started_at=datetime.now(UTC),
    )

    path = _department_artifact_path(product_name, department_name, root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    result.add_artifact(str(path))
    result.complete()

    return path


def retrieve_department_artifact(
    product_name: str,
    department_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    artifact = _load_department(product_name, department_name, root_path)

    if artifact is None:
        raise ValueError(
            f"no Department artifact found for product: {product_name}/{department_name}"
        )

    return artifact
