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


def test_dispatcher_dispatches_ready_nodes():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    ready_nodes = [DummyNode("A"), DummyNode("B")]

    dispatcher = ManufacturingDispatcher()

    dispatched = dispatcher.dispatch(ready_nodes)

    assert {entry["node_id"] for entry in dispatched} == {"A", "B"}


def test_dispatcher_returns_deterministic_order_regardless_of_input_order():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    dispatcher = ManufacturingDispatcher()

    dispatched = dispatcher.dispatch([DummyNode("C"), DummyNode("A"), DummyNode("B")])

    assert [entry["node_id"] for entry in dispatched] == ["A", "B", "C"]


def test_dispatcher_is_deterministic_across_calls():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    ready_nodes = [DummyNode("B"), DummyNode("A")]

    dispatcher = ManufacturingDispatcher()

    r1 = [entry["node_id"] for entry in dispatcher.dispatch(ready_nodes)]
    r2 = [entry["node_id"] for entry in dispatcher.dispatch(ready_nodes)]

    assert r1 == r2 == ["A", "B"]


def test_dispatcher_handles_empty_list():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    dispatcher = ManufacturingDispatcher()

    assert dispatcher.dispatch([]) == []


def test_dispatcher_handles_none():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    dispatcher = ManufacturingDispatcher()

    assert dispatcher.dispatch(None) == []


def test_dispatcher_result_references_original_node_and_status():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    node = DummyNode("A")
    dispatcher = ManufacturingDispatcher()

    dispatched = dispatcher.dispatch([node])

    assert len(dispatched) == 1
    assert dispatched[0]["node_id"] == "A"
    assert dispatched[0]["node"] is node
    assert dispatched[0]["status"] == "dispatched"


def test_dispatcher_does_not_mutate_input_list():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    ready_nodes = [DummyNode("C"), DummyNode("A")]
    original_order = list(ready_nodes)

    dispatcher = ManufacturingDispatcher()
    dispatcher.dispatch(ready_nodes)

    assert ready_nodes == original_order


def test_dispatcher_is_stateless_between_instances():
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    ready_nodes = [DummyNode("A"), DummyNode("B")]

    first_dispatcher = ManufacturingDispatcher()
    first_dispatcher.dispatch(ready_nodes)

    second_dispatcher = ManufacturingDispatcher()
    dispatched = second_dispatcher.dispatch(ready_nodes)

    assert [entry["node_id"] for entry in dispatched] == ["A", "B"]


def test_dispatcher_consumes_scheduler_output_directly():
    from MANUFACTURING_CENTER.manufacturing_scheduler import ManufacturingScheduler
    from MANUFACTURING_CENTER.manufacturing_dispatcher import ManufacturingDispatcher

    graph = DummyExecutionGraph([
        DummyNode("A"),
        DummyNode("B", ["A"]),
    ])

    scheduler = ManufacturingScheduler()
    dispatcher = ManufacturingDispatcher()

    ready = scheduler.next_ready(graph, completed=set())
    dispatched = dispatcher.dispatch(ready)

    assert [entry["node_id"] for entry in dispatched] == ["A"]

    ready = scheduler.next_ready(graph, completed={"A"})
    dispatched = dispatcher.dispatch(ready)

    assert [entry["node_id"] for entry in dispatched] == ["B"]
