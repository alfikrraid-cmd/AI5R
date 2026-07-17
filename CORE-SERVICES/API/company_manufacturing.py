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
from MANUFACTURING.company_recipe_registration import register_company_manufacturing
from MANUFACTURING_CENTER.manufacturing_result import ManufacturingResult
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus

from .digital_factory_bootstrap import get_digital_factory

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def _product_artifact_path(product_name: str, root_path: Path | str) -> Path:
    return Path(root_path) / "PRODUCTS" / product_name / "product_artifact.json"


def _company_artifact_path(product_name: str, root_path: Path | str) -> Path:
    return Path(root_path) / "PRODUCTS" / product_name / "company_artifact.json"


def manufacture_company(
    product_name: str,
    company_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    if not _product_artifact_path(product_name, root_path).exists():
        raise ValueError(f"owning Product does not exist: {product_name}")

    if _company_artifact_path(product_name, root_path).exists():
        raise ValueError(f"Company already manufactured for product: {product_name}")

    factory = get_digital_factory()
    register_company_manufacturing(factory)

    order = ManufacturingOrder(
        order_id=f"MO-COMPANY-{uuid4().hex[:8].upper()}",
        product_name=product_name,
        product_type="COMPANY",
        requested_by="AI5R",
        requirements={"company_name": company_name},
    )

    response = factory.manufacture_order(order)

    artifact = response.output["company_artifact"]

    published_path = publish_company_artifact(product_name, artifact, root_path)

    return {
        "status": str(response.status),
        "order_id": order.order_id,
        "artifact_path": str(published_path),
        "company_artifact": artifact,
    }


def publish_company_artifact(
    product_name: str,
    artifact: dict[str, Any],
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> Path:
    """The publishing mechanism: persists a Company Artifact the capability produced."""

    result = ManufacturingResult(
        manufacturing_id=f"MR-COMPANY-{uuid4().hex[:8].upper()}",
        status=ManufacturingStatus.MANUFACTURING,
        started_at=datetime.now(UTC),
    )

    path = _company_artifact_path(product_name, root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    result.add_artifact(str(path))
    result.complete()

    return path


def retrieve_company_artifact(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    path = _company_artifact_path(product_name, root_path)

    if not path.exists():
        raise ValueError(f"no Company artifact found for product: {product_name}")

    return json.loads(path.read_text(encoding="utf-8"))
