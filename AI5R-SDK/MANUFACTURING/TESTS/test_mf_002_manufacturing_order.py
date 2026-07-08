from MANUFACTURING import (
    ManufacturingObjectType,
    ManufacturingOrder,
    ManufacturingOrderPriority,
    ManufacturingOrderStatus,
)


def test_manufacturing_order_is_valid():
    order = ManufacturingOrder(
        order_id="MO-001",
        product_name="AI5R Studio Website",
        product_type="WEBSITE",
        requested_by="Founder",
    )

    assert order.validate() is True


def test_manufacturing_order_reuses_manufacturing_object():
    order = ManufacturingOrder(
        order_id="MO-002",
        product_name="Marketing Executive AI",
        product_type="AI_AGENT",
        requested_by="Founder",
    )

    obj = order.to_manufacturing_object()

    assert obj.object_id == "MO-002"
    assert obj.object_type == ManufacturingObjectType.MANUFACTURING_ORDER
    assert obj.name == "Marketing Executive AI"
    assert obj.metadata["product_type"] == "AI_AGENT"
    assert obj.metadata["requested_by"] == "Founder"


def test_manufacturing_order_has_default_status_and_priority():
    order = ManufacturingOrder(
        order_id="MO-003",
        product_name="RaiShine OS",
        product_type="ENTERPRISE_OS",
        requested_by="Founder",
    )

    assert order.status == ManufacturingOrderStatus.DRAFT
    assert order.priority == ManufacturingOrderPriority.MEDIUM


def test_manufacturing_order_rejects_missing_required_fields():
    order = ManufacturingOrder(
        order_id="",
        product_name="",
        product_type="",
        requested_by="",
    )

    assert order.validate() is False


def test_manufacturing_order_ready_for_planning_only_when_draft_and_valid():
    order = ManufacturingOrder(
        order_id="MO-004",
        product_name="Alleira Dashboard",
        product_type="DASHBOARD",
        requested_by="Founder",
    )

    assert order.is_ready_for_planning() is True


def test_manufacturing_order_contains_requirements():
    order = ManufacturingOrder(
        order_id="MO-005",
        product_name="Presentation Builder",
        product_type="SAAS",
        requested_by="Founder",
        requirements={
            "editable": True,
            "export": "pptx",
        },
    )

    obj = order.to_manufacturing_object()

    assert obj.metadata["requirements"]["editable"] is True
    assert obj.metadata["requirements"]["export"] == "pptx"
