import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import OrganizationBuilder


def test_empty_organization():
    runtime = (
        OrganizationBuilder("AI5R")
        .build()
    )

    assert runtime.name == "AI5R"
    assert runtime.departments == []
    assert runtime.employees == []
    assert runtime.workflows == []


def test_build_complete_organization():
    runtime = (
        OrganizationBuilder("AI5R")
        .add_department("Engineering")
        .add_department("Finance")
        .add_employee("EMP-001")
        .add_employee("EMP-002")
        .add_workflow("WF-001")
        .build()
    )

    assert runtime.departments == [
        "Engineering",
        "Finance",
    ]

    assert runtime.employees == [
        "EMP-001",
        "EMP-002",
    ]

    assert runtime.workflows == [
        "WF-001",
    ]


def test_builder_is_chainable():
    builder = OrganizationBuilder("Factory")

    assert builder.add_department("Ops") is builder
    assert builder.add_employee("E-01") is builder
    assert builder.add_workflow("WF") is builder
