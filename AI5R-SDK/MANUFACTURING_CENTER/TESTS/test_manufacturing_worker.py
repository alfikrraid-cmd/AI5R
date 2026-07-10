import pytest


class DummyNode:
    def __init__(self, node_id, dependencies=None):
        self.node_id = node_id
        self.dependencies = dependencies or []
        self.executed = False


class NodeWithoutNodeId:
    pass


def test_worker_executes_valid_node_and_returns_success():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    node = DummyNode("A")
    worker = ManufacturingWorker()

    result = worker.execute(node)

    assert result["node_id"] == "A"
    assert result["status"] == "SUCCESS"


def test_worker_result_references_original_node():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    node = DummyNode("A")
    worker = ManufacturingWorker()

    result = worker.execute(node)

    assert result["node"] is node


def test_worker_result_includes_execution_metadata():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    worker = ManufacturingWorker()

    result = worker.execute(DummyNode("A"))

    assert "metadata" in result
    assert isinstance(result["metadata"], dict)


def test_worker_does_not_execute_business_logic():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    node = DummyNode("A")
    worker = ManufacturingWorker()

    worker.execute(node)

    assert node.executed is False


def test_worker_is_deterministic_across_calls():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    node = DummyNode("A")
    worker = ManufacturingWorker()

    r1 = worker.execute(node)
    r2 = worker.execute(node)

    assert r1["node_id"] == r2["node_id"]
    assert r1["status"] == r2["status"]
    assert r1["metadata"] == r2["metadata"]


def test_worker_is_stateless_between_instances():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    node = DummyNode("A")

    first_worker = ManufacturingWorker()
    first_result = first_worker.execute(node)

    second_worker = ManufacturingWorker()
    second_result = second_worker.execute(node)

    assert first_result["status"] == second_result["status"] == "SUCCESS"


def test_worker_raises_on_none_node():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    worker = ManufacturingWorker()

    with pytest.raises(ValueError):
        worker.execute(None)


def test_worker_raises_on_node_without_node_id():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    worker = ManufacturingWorker()

    with pytest.raises(ValueError):
        worker.execute(NodeWithoutNodeId())


def test_worker_raises_on_empty_node_id():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    worker = ManufacturingWorker()

    with pytest.raises(ValueError):
        worker.execute(DummyNode(""))


def test_worker_raises_on_non_string_node_id():
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    worker = ManufacturingWorker()

    with pytest.raises(ValueError):
        worker.execute(DummyNode(123))


def test_runtime_defaults_to_a_manufacturing_worker_instance():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    runtime = ManufacturingRuntime()

    assert isinstance(runtime.worker, ManufacturingWorker)


def test_runtime_accepts_injected_custom_worker():
    from MANUFACTURING_CENTER.manufacturing_runtime import ManufacturingRuntime
    from MANUFACTURING_CENTER.manufacturing_worker import ManufacturingWorker

    class CustomWorker(ManufacturingWorker):
        pass

    custom_worker = CustomWorker()

    runtime = ManufacturingRuntime(worker=custom_worker)

    assert runtime.worker is custom_worker
