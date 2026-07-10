from pytest import raises

from MANUFACTURING_CENTER.manufacturing_payload_merger import (
    ManufacturingPayloadMerger,
)


def test_merge_non_conflicting_payloads() -> None:
    merged = ManufacturingPayloadMerger().merge(
        base={
            "order_id": "MO-001",
        },
        results={
            "ARCHITECTURE": {
                "architecture_ready": True,
            },
            "IMPLEMENTATION": {
                "implementation_ready": True,
            },
        },
    )

    assert merged["order_id"] == "MO-001"
    assert merged["architecture_ready"] is True
    assert merged["implementation_ready"] is True


def test_merge_artifacts() -> None:
    merged = ManufacturingPayloadMerger().merge(
        base={},
        results={
            "A": {
                "artifacts": ["a.zip"],
            },
            "B": {
                "artifacts": ["b.zip"],
            },
        },
    )

    assert merged["artifacts"] == [
        "a.zip",
        "b.zip",
    ]


def test_duplicate_artifacts_removed() -> None:
    merged = ManufacturingPayloadMerger().merge(
        base={},
        results={
            "A": {
                "artifacts": ["a.zip"],
            },
            "B": {
                "artifacts": [
                    "a.zip",
                    "b.zip",
                ],
            },
        },
    )

    assert merged["artifacts"] == [
        "a.zip",
        "b.zip",
    ]


def test_conflicting_values_raise() -> None:
    with raises(ValueError):
        ManufacturingPayloadMerger().merge(
            base={},
            results={
                "A": {
                    "version": "1",
                },
                "B": {
                    "version": "2",
                },
            },
        )


def test_single_capability_can_update_base_value() -> None:
    merged = ManufacturingPayloadMerger().merge(
        base={
            "requirements": {},
        },
        results={
            "REQUIREMENTS": {
                "requirements": True,
            },
        },
    )

    assert merged["requirements"] is True


def test_unchanged_echo_does_not_conflict_with_update() -> None:
    merged = ManufacturingPayloadMerger().merge(
        base={
            "status": "draft",
        },
        results={
            "A": {
                "status": "draft",
                "a_ready": True,
            },
            "B": {
                "status": "complete",
                "b_ready": True,
            },
        },
    )

    assert merged["status"] == "complete"
    assert merged["a_ready"] is True
    assert merged["b_ready"] is True
