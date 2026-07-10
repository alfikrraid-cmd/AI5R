import sys

import pytest

from ORGANIZATION.role_assignment import RoleAssignment
from ORGANIZATION.role_execution_result import RoleExecutionResult


def make_assignment(assignment_id, role_id="ROLE-001"):
    return RoleAssignment(
        assignment_id=assignment_id,
        role_id=role_id,
        work_order_id="WO-001",
        priority="NORMAL",
        status="PENDING",
    )


class RecordingExecutor:
    def __init__(self, status_map=None, raise_for=None):
        self.calls = []
        self.status_map = status_map or {}
        self.raise_for = raise_for or set()

    def execute(self, assignment):
        self.calls.append(assignment.assignment_id)

        if assignment.assignment_id in self.raise_for:
            raise RuntimeError(f"executor failed for {assignment.assignment_id}")

        status = self.status_map.get(assignment.assignment_id, "SUCCESS")

        return RoleExecutionResult(
            execution_id=f"EXEC-{assignment.assignment_id}",
            assignment_id=assignment.assignment_id,
            role_id=assignment.role_id,
            status=status,
        )


class RecordingScheduler:
    def __init__(self, ordered_ids):
        self.ordered_ids = ordered_ids
        self.calls = 0

    def order(self, assignments):
        self.calls += 1
        by_id = {a.assignment_id: a for a in assignments}
        return [by_id[assignment_id] for assignment_id in self.ordered_ids]


def test_execute_with_empty_assignments_returns_empty_list():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    runtime = OrganizationRuntime(assignment_executor=RecordingExecutor())

    assert runtime.execute([]) == []


def test_execute_single_assignment_returns_single_result():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor()
    runtime = OrganizationRuntime(assignment_executor=executor)

    results = runtime.execute([make_assignment("A")])

    assert len(results) == 1
    assert results[0].assignment_id == "A"
    assert results[0].status == "SUCCESS"


def test_execute_multiple_assignments_returns_all_results():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor()
    runtime = OrganizationRuntime(assignment_executor=executor)

    assignments = [make_assignment("A"), make_assignment("B"), make_assignment("C")]
    results = runtime.execute(assignments)

    assert {result.assignment_id for result in results} == {"A", "B", "C"}


def test_execute_produces_deterministic_order_regardless_of_input_order():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor()
    runtime = OrganizationRuntime(assignment_executor=executor)

    assignments = [make_assignment("C"), make_assignment("A"), make_assignment("B")]
    results = runtime.execute(assignments)

    assert [result.assignment_id for result in results] == ["A", "B", "C"]
    assert executor.calls == ["A", "B", "C"]


def test_execute_uses_injected_executor():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor()
    runtime = OrganizationRuntime(assignment_executor=executor)

    runtime.execute([make_assignment("A"), make_assignment("B")])

    assert executor.calls == ["A", "B"]


def test_execute_propagates_executor_failure():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor(raise_for={"B"})
    runtime = OrganizationRuntime(assignment_executor=executor)

    with pytest.raises(RuntimeError):
        runtime.execute([make_assignment("A"), make_assignment("B")])


def test_execute_raises_without_injected_executor():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    runtime = OrganizationRuntime()

    with pytest.raises(ValueError):
        runtime.execute([make_assignment("A")])


def test_collect_results_returns_defensive_copy():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    runtime = OrganizationRuntime()

    result = RoleExecutionResult(
        execution_id="EXEC-A",
        assignment_id="A",
        role_id="ROLE-001",
        status="SUCCESS",
    )
    results = [result]

    collected = runtime.collect_results(results)
    results.append(result)

    assert len(collected) == 1
    assert collected == [result]


def test_execute_is_stateless_across_multiple_calls():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    executor = RecordingExecutor()
    runtime = OrganizationRuntime(assignment_executor=executor)

    assignments = [make_assignment("A"), make_assignment("B")]

    first = [result.assignment_id for result in runtime.execute(assignments)]
    second = [result.assignment_id for result in runtime.execute(assignments)]

    assert first == second == ["A", "B"]
    assert executor.calls == ["A", "B", "A", "B"]


def test_runtime_supports_construction_without_arguments():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    runtime = OrganizationRuntime()

    ordered = runtime.assign([make_assignment("B"), make_assignment("A")])

    assert [assignment.assignment_id for assignment in ordered] == ["A", "B"]


def test_assign_uses_injected_scheduler_when_provided():
    from ORGANIZATION.organization_runtime import OrganizationRuntime

    scheduler = RecordingScheduler(ordered_ids=["B", "A"])
    runtime = OrganizationRuntime(scheduler=scheduler)

    ordered = runtime.assign([make_assignment("A"), make_assignment("B")])

    assert [assignment.assignment_id for assignment in ordered] == ["B", "A"]
    assert scheduler.calls == 1


def test_organization_runtime_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.organization_runtime  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
