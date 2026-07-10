import pytest

from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def test_status_is_string_enum():
    assert ManufacturingStatus.PENDING == "pending"
    assert str(ManufacturingStatus.COMPLETED) == "completed"


def test_terminal_statuses():
    assert ManufacturingStatus.COMPLETED.is_terminal is True
    assert ManufacturingStatus.FAILED.is_terminal is True
    assert ManufacturingStatus.CANCELLED.is_terminal is True
    assert ManufacturingStatus.MANUFACTURING.is_terminal is False


def test_active_statuses():
    assert ManufacturingStatus.PENDING.is_active is True
    assert ManufacturingStatus.TESTING.is_active is True
    assert ManufacturingStatus.COMPLETED.is_active is False


def test_from_value():
    assert (
        ManufacturingStatus.from_value("manufacturing")
        is ManufacturingStatus.MANUFACTURING
    )


def test_from_value_rejects_invalid_status():
    with pytest.raises(
        ValueError,
        match="Invalid ManufacturingStatus value",
    ):
        ManufacturingStatus.from_value("unknown")
