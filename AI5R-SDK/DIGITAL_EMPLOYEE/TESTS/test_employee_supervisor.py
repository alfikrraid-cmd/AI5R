from DIGITAL_EMPLOYEE.SUPERVISOR import (
    EmployeeSupervisorStore,
    SupervisorDecision,
)


def test_review_creation():
    store = EmployeeSupervisorStore()

    review = store.review(
        employee_id="EMP-001",
        supervisor_id="EMP-999",
        decision=SupervisorDecision.APPROVED,
        comments="Looks good",
    )

    assert review.employee_id == "EMP-001"
    assert review.supervisor_id == "EMP-999"
    assert review.decision == SupervisorDecision.APPROVED


def test_latest_review():
    store = EmployeeSupervisorStore()

    store.review(
        "EMP-001",
        "EMP-900",
        "APPROVED",
    )

    latest = store.review(
        "EMP-001",
        "EMP-901",
        "REVISION_REQUIRED",
    )

    assert store.latest("EMP-001") is latest


def test_review_count():
    store = EmployeeSupervisorStore()

    store.review("EMP-001", "SUP-1", "APPROVED")
    store.review("EMP-001", "SUP-2", "REJECTED")
    store.review("EMP-002", "SUP-3", "APPROVED")

    assert store.count() == 3
    assert store.count("EMP-001") == 2


def test_snapshot():
    store = EmployeeSupervisorStore()

    review = store.review(
        "EMP-001",
        "SUP-1",
        "APPROVED",
    )

    snapshot = store.snapshot()

    assert review.review_id in snapshot
