from DIGITAL_EMPLOYEE.PERFORMANCE import PerformanceEngine


def test_register():
    engine = PerformanceEngine()

    employee = engine.register("EMP-001")

    assert employee.employee_id == "EMP-001"
    assert employee.score == 100


def test_success():
    engine = PerformanceEngine()

    employee = engine.record_success("EMP-001")

    assert employee.completed_tasks == 1
    assert employee.success_rate == 100


def test_failure():
    engine = PerformanceEngine()

    employee = engine.record_failure("EMP-001")

    assert employee.failed_tasks == 1
    assert employee.success_rate == 0


def test_ranking():
    engine = PerformanceEngine()

    engine.record_success("EMP-A")
    engine.record_success("EMP-A")

    engine.record_success("EMP-B")
    engine.record_failure("EMP-B")

    ranking = engine.ranking()

    assert ranking[0].employee_id == "EMP-A"


def test_snapshot():
    engine = PerformanceEngine()

    employee = engine.record_success("EMP-001")

    snapshot = engine.snapshot()

    assert employee.employee_id in snapshot
