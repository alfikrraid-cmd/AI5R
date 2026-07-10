from pathlib import Path

import pytest

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingOrderStatus,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory

from MANUFACTURING_CENTER.manufacturing_center import ManufacturingCenter
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def make_factory() -> DigitalFactory:
    factory = DigitalFactory(
        factory_id="DF-CENTER-001",
        factory_name="AI5R Digital Factory",
    )

    factory.register_recipe(
        ManufacturingRecipe(
            recipe_id="RCP-CENTER-001",
            recipe_name="Center Recipe",
            product_type="WEBSITE",
            dbom_id="DBOM-CENTER-001",
            production_line_id="LINE-CENTER-001",
            qa_policy_id="QA-CENTER-001",
            packaging_id="PKG-CENTER-001",
            deployment_id="DEPLOY-CENTER-001",
        ),
        ProductionLine(
            line_id="LINE-CENTER-001",
            line_name="Center Line",
            product_type="WEBSITE",
            capability_ids=("BUILD_PRODUCT",),
        ),
    )

    def build_product(request):
        return {
            **request.payload,
            "built": True,
            "artifacts": ["build/site.zip"],
        }

    factory.register_capability(
        "BUILD_PRODUCT",
        build_product,
    )
    return factory


def make_order() -> ManufacturingOrder:
    return ManufacturingOrder(
        order_id="MO-CENTER-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Chief",
        metadata={"owner": "Maya"},
    )


def test_manufacture_returns_completed_result(
    tmp_path: Path,
) -> None:
    center = ManufacturingCenter(
        factory=make_factory(),
        workspace=tmp_path,
        metadata={"source": "studio"},
    )

    result = center.manufacture(order=make_order())

    assert result.status is ManufacturingStatus.COMPLETED
    assert result.artifacts == ["build/site.zip"]
    assert result.metadata["owner"] == "Maya"
    assert result.metadata["source"] == "studio"
    assert result.metadata["runtime_output"]["built"] is True


def test_properties(tmp_path: Path) -> None:
    center = ManufacturingCenter(
        factory=make_factory(),
        workspace=tmp_path,
    )

    assert center.factory_id == "DF-CENTER-001"
    assert center.factory_name == "AI5R Digital Factory"
    assert center.workspace_exists is True


def test_workspace_must_be_path() -> None:
    with pytest.raises(TypeError, match="workspace must be a Path"):
        ManufacturingCenter(
            factory=make_factory(),
            workspace="/tmp/ai5r",
        )


def test_workspace_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="workspace must be absolute"):
        ManufacturingCenter(
            factory=make_factory(),
            workspace=Path("relative/path"),
        )


def test_rejects_order_not_ready(
    tmp_path: Path,
) -> None:
    order = ManufacturingOrder(
        order_id="MO-CENTER-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Chief",
        status=ManufacturingOrderStatus.COMPLETED,
        metadata={"owner": "Maya"},
    )

    center = ManufacturingCenter(
        factory=make_factory(),
        workspace=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="is_ready_for_planning",
    ):
        center.manufacture(order=order)


def test_runtime_failure_returns_failed_result(
    tmp_path: Path,
) -> None:
    factory = make_factory()

    def broken_capability(request):
        raise RuntimeError("build failed")

    factory.register_capability(
        "BUILD_PRODUCT",
        broken_capability,
    )

    center = ManufacturingCenter(
        factory=factory,
        workspace=tmp_path,
    )

    result = center.manufacture(order=make_order())

    assert result.status is ManufacturingStatus.FAILED
    assert result.logs == ["Manufacturing failed: build failed"]


def test_does_not_mutate_order_metadata(
    tmp_path: Path,
) -> None:
    order = make_order()
    original = dict(order.metadata)

    center = ManufacturingCenter(
        factory=make_factory(),
        workspace=tmp_path,
        metadata={"source": "studio"},
    )

    center.manufacture(order=order)

    assert order.metadata == original
