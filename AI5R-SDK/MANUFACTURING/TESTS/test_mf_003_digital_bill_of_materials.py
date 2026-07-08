from MANUFACTURING import (
    DBOMComponent,
    DBOMComponentStatus,
    DBOMComponentType,
    DigitalBillOfMaterials,
    ManufacturingObjectType,
)


def test_dbom_component_is_valid():
    component = DBOMComponent(
        component_id="COMP-001",
        name="Frontend",
        component_type=DBOMComponentType.FRONTEND,
        status=DBOMComponentStatus.AVAILABLE,
    )

    assert component.validate() is True


def test_dbom_is_valid():
    dbom = DigitalBillOfMaterials(
        dbom_id="DBOM-WEB-001",
        product_type="WEBSITE",
        components=(
            DBOMComponent(
                component_id="COMP-001",
                name="Frontend",
                component_type=DBOMComponentType.FRONTEND,
                status=DBOMComponentStatus.AVAILABLE,
            ),
        ),
    )

    assert dbom.validate() is True


def test_dbom_rejects_duplicate_components():
    component = DBOMComponent(
        component_id="COMP-001",
        name="Frontend",
        component_type=DBOMComponentType.FRONTEND,
    )

    dbom = DigitalBillOfMaterials(
        dbom_id="DBOM-WEB-002",
        product_type="WEBSITE",
        components=(component, component),
    )

    assert dbom.validate() is False


def test_dbom_detects_missing_components():
    dbom = DigitalBillOfMaterials(
        dbom_id="DBOM-AI-001",
        product_type="AI_AGENT",
        components=(
            DBOMComponent(
                component_id="COMP-KNOWLEDGE",
                name="Knowledge Base",
                component_type=DBOMComponentType.KNOWLEDGE,
                status=DBOMComponentStatus.AVAILABLE,
            ),
            DBOMComponent(
                component_id="COMP-TOOL",
                name="Tool Runtime",
                component_type=DBOMComponentType.TOOL,
                status=DBOMComponentStatus.MISSING,
            ),
        ),
    )

    missing = dbom.missing_components()

    assert len(missing) == 1
    assert missing[0].name == "Tool Runtime"
    assert dbom.is_ready_for_manufacturing() is False


def test_dbom_ready_when_no_missing_components():
    dbom = DigitalBillOfMaterials(
        dbom_id="DBOM-PPT-001",
        product_type="PRESENTATION",
        components=(
            DBOMComponent(
                component_id="COMP-CONTENT",
                name="Storyline",
                component_type=DBOMComponentType.CONTENT,
                status=DBOMComponentStatus.AVAILABLE,
            ),
            DBOMComponent(
                component_id="COMP-MEDIA",
                name="Slide Visuals",
                component_type=DBOMComponentType.MEDIA,
                status=DBOMComponentStatus.PLANNED,
            ),
        ),
    )

    assert dbom.is_ready_for_manufacturing() is True


def test_dbom_reuses_manufacturing_object():
    dbom = DigitalBillOfMaterials(
        dbom_id="DBOM-ERP-001",
        product_type="ENTERPRISE_OS",
        components=(
            DBOMComponent(
                component_id="COMP-WORKFLOW",
                name="Workflow",
                component_type=DBOMComponentType.WORKFLOW,
            ),
        ),
    )

    obj = dbom.to_manufacturing_object()

    assert obj.object_id == "DBOM-ERP-001"
    assert obj.object_type == ManufacturingObjectType.DBOM
    assert obj.name == "ENTERPRISE_OS DBOM"
    assert obj.metadata["component_count"] == 1


def test_dbom_component_types_cover_digital_products():
    required = {
        "FRONTEND",
        "BACKEND",
        "DATABASE",
        "API",
        "AUTH",
        "UI",
        "KNOWLEDGE",
        "PROMPT",
        "MEMORY",
        "TOOL",
        "WORKFLOW",
        "DOCUMENT",
        "DASHBOARD",
        "TEST",
        "DEPLOYMENT",
        "CONTENT",
        "MEDIA",
        "POLICY",
    }

    actual = {item.value for item in DBOMComponentType}

    assert required.issubset(actual)
