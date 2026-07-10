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
