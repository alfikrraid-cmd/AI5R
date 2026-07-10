import pytest


class DummyNode:
    def __init__(self, node_id, dependencies=None):
        self.node_id = node_id
        self.dependencies = dependencies or []


class DummyExecutionGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def all_node_ids(self):
        return {n.node_id for n in self.nodes}

    def ready_nodes(self, completed):
        return [
            n
            for n in self.nodes
            if n.node_id not in completed
            and all(dep in completed for dep in n.dependencies)
        ]


def test_runtime_executes_all_independent_nodes():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B"),
    ])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    assert {entry["node_id"] for entry in dispatched} == {"A", "B"}


def test_runtime_respects_dependencies_across_iterations():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
        DummyNode("C", ["B"]),
    ])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    assert [entry["node_id"] for entry in dispatched] == ["A", "B", "C"]


def test_runtime_marks_dispatched_nodes_as_completed():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
    ])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    dispatched_ids = {entry["node_id"] for entry in dispatched}
    assert dispatched_ids == graph.all_node_ids()


def test_runtime_deterministic_order_within_a_level():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("C"),
        DummyNode("A"),
        DummyNode("B"),
    ])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    assert [entry["node_id"] for entry in dispatched] == ["A", "B", "C"]


def test_runtime_is_deterministic_across_runs():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
        DummyNode("C", ["A"]),
    ])

    runtime = ManufacturingRuntime()

    r1 = [entry["node_id"] for entry in runtime.run(graph)]
    r2 = [entry["node_id"] for entry in runtime.run(graph)]

    assert r1 == r2 == ["A", "B", "C"]


def test_runtime_handles_empty_graph():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([])

    runtime = ManufacturingRuntime()

    assert runtime.run(graph) == []


def test_runtime_handles_none_graph():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    runtime = ManufacturingRuntime()

    assert runtime.run(None) == []


def test_runtime_stops_when_no_further_work_can_become_ready():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["MISSING"]),
    ])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    assert [entry["node_id"] for entry in dispatched] == ["A"]


def test_runtime_dispatch_entries_expose_node_id_node_and_status():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([DummyNode("A")])

    runtime = ManufacturingRuntime()

    dispatched = runtime.run(graph)

    assert len(dispatched) == 1
    assert dispatched[0]["node_id"] == "A"
    assert dispatched[0]["node"] is graph.nodes[0]
    assert dispatched[0]["status"] == "dispatched"


def test_runtime_uses_injected_scheduler_and_dispatcher():
    from MANUFACTURING_CENTER.manufacturing_scheduler import ManufacturingScheduler
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    scheduler = ManufacturingScheduler()
    dispatcher = ManufacturingDispatcher()

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B", ["A"])])

    runtime = ManufacturingRuntime(scheduler=scheduler, dispatcher=dispatcher)

    dispatched = [entry["node_id"] for entry in runtime.run(graph)]

    assert dispatched == ["A", "B"]


def test_runtime_is_stateless_between_instances():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B")])

    first_runtime = ManufacturingRuntime()
    first_runtime.run(graph)

    second_runtime = ManufacturingRuntime()
    dispatched = [entry["node_id"] for entry in second_runtime.run(graph)]

    assert dispatched == ["A", "B"]


class RecordingWorker:
    """Test double that mimics ManufacturingWorker.execute() while
    letting tests control the returned status per node_id."""

    def __init__(self, statuses=None):
        self.calls = []
        self.statuses = statuses or {}

    def execute(self, node):
        self.calls.append(node.node_id)
        status = self.statuses.get(node.node_id, "SUCCESS")

        return {
            "node_id": node.node_id,
            "node": node,
            "status": status,
            "metadata": {"simulated": True},
        }


def test_execute_returns_manufacturing_execution_result():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B")])

    runtime = ManufacturingRuntime()

    result = runtime.execute(graph)

    assert isinstance(result, ManufacturingExecutionResult)


def test_execute_calls_worker_for_each_dispatched_node():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B")])
    worker = RecordingWorker()

    runtime = ManufacturingRuntime(worker=worker)
    runtime.execute(graph)

    assert set(worker.calls) == {"A", "B"}


def test_execute_marks_nodes_completed_only_after_success():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
    ])

    runtime = ManufacturingRuntime()

    result = runtime.execute(graph)

    assert result.completed_nodes == ("A", "B")
    assert result.execution_order == ("A", "B")
    assert result.status == "COMPLETED"


def test_execute_preserves_deterministic_order_within_a_level():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("C"),
        DummyNode("A"),
        DummyNode("B"),
    ])

    runtime = ManufacturingRuntime()

    result = runtime.execute(graph)

    assert result.execution_order == ("A", "B", "C")


def test_execute_stops_when_worker_returns_failed():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
        DummyNode("C", ["B"]),
    ])
    worker = RecordingWorker(statuses={"B": "FAILED"})

    runtime = ManufacturingRuntime(worker=worker)

    result = runtime.execute(graph)

    assert result.status == "FAILED"
    assert result.failed_nodes == ("B",)
    assert result.completed_nodes == ("A",)
    assert "C" not in result.execution_order
    assert "C" not in worker.calls


def test_execute_is_deterministic_across_calls():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
        DummyNode("C", ["A"]),
    ])

    runtime = ManufacturingRuntime()

    r1 = runtime.execute(graph)
    r2 = runtime.execute(graph)

    assert r1.execution_order == r2.execution_order == ("A", "B", "C")
    assert r1.status == r2.status == "COMPLETED"


def test_execute_handles_empty_graph():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([])

    runtime = ManufacturingRuntime()

    result = runtime.execute(graph)

    assert result.status == "COMPLETED"
    assert result.completed_nodes == ()
    assert result.failed_nodes == ()
    assert result.execution_order == ()


def test_execute_handles_none_graph():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    runtime = ManufacturingRuntime()

    result = runtime.execute(None)

    assert result.status == "COMPLETED"
    assert result.completed_nodes == ()
    assert result.failed_nodes == ()
    assert result.execution_order == ()


def test_execute_uses_injected_scheduler_dispatcher_and_worker():
    from MANUFACTURING_CENTER.manufacturing_scheduler import ManufacturingScheduler
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    scheduler = ManufacturingScheduler()
    dispatcher = ManufacturingDispatcher()
    worker = ManufacturingWorker()

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B", ["A"])])

    runtime = ManufacturingRuntime(
        scheduler=scheduler,
        dispatcher=dispatcher,
        worker=worker,
    )

    result = runtime.execute(graph)

    assert result.execution_order == ("A", "B")
    assert result.status == "COMPLETED"


def test_run_still_returns_raw_dispatch_list_and_does_not_call_worker():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime

    graph = DummyExecutionGraph([DummyNode("A"), DummyNode("B", ["A"])])
    worker = RecordingWorker()

    runtime = ManufacturingRuntime(worker=worker)

    dispatched = runtime.run(graph)

    assert [entry["node_id"] for entry in dispatched] == ["A", "B"]
    assert worker.calls == []
