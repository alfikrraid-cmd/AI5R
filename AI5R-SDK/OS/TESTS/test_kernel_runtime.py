import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OS.kernel_runtime import KernelRuntime


def test_kernel_runtime_executes_process():
    runtime = KernelRuntime()

    runtime.identity_service.register(
        "emp-001",
        "DIGITAL_EMPLOYEE",
        "Worker One",
    )

    runtime.capability_service.register(
        "cap-001",
        "emp-001",
        "Reasoning",
    )

    runtime.resource_manager.register(
        "res-001",
        "CPU",
        "kernel",
    )

    result = runtime.execute(
        runtime_id="run-001",
        process_id="proc-001",
        identity_id="emp-001",
        capability_id="cap-001",
        resource_id="res-001",
        payload={"task": "think"},
    )

    assert result.status == "EXECUTED"
    assert result.output["identity"] == "Worker One"
    assert result.output["capability"] == "Reasoning"
    assert result.output["resource"] == "CPU"
    assert result.output["payload"]["task"] == "think"


def test_kernel_runtime_creates_context_when_missing():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    result = runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    context = runtime.context_manager.get_process_context("proc-001")

    assert context is not None
    assert result.output["context_id"] == context.context_id


def test_kernel_runtime_updates_context():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    context = runtime.context_manager.get_process_context("proc-001")

    assert context.data["last_runtime_id"] == "run-001"
    assert context.data["last_status"] == "EXECUTED"


def test_kernel_runtime_releases_resource_after_execution():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    assert runtime.resource_manager.get("res-001").status == "AVAILABLE"


def test_kernel_runtime_rejects_duplicate_runtime_id():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    try:
        runtime.execute(
            "run-001",
            "proc-002",
            "emp-001",
            "cap-001",
            "res-001",
        )
        assert False
    except ValueError as error:
        assert str(error) == "runtime already exists"


def test_kernel_runtime_requires_identity():
    runtime = KernelRuntime()

    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    try:
        runtime.execute(
            "run-001",
            "proc-001",
            "missing",
            "cap-001",
            "res-001",
        )
        assert False
    except ValueError as error:
        assert str(error) == "identity not found"


def test_kernel_runtime_requires_capability():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    try:
        runtime.execute(
            "run-001",
            "proc-001",
            "emp-001",
            "missing",
            "res-001",
        )
        assert False
    except ValueError as error:
        assert str(error) == "capability not found"


def test_kernel_runtime_requires_resource():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")

    try:
        runtime.execute(
            "run-001",
            "proc-001",
            "emp-001",
            "cap-001",
            "missing",
        )
        assert False
    except ValueError as error:
        assert str(error) == "resource not found"


def test_kernel_runtime_get_result():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    result = runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    assert runtime.get_result("run-001") == result


def test_kernel_runtime_list_results():
    runtime = KernelRuntime()

    runtime.identity_service.register("emp-001", "DIGITAL_EMPLOYEE", "Worker")
    runtime.capability_service.register("cap-001", "emp-001", "Planning")
    runtime.resource_manager.register("res-001", "CPU", "kernel")

    runtime.execute(
        "run-001",
        "proc-001",
        "emp-001",
        "cap-001",
        "res-001",
    )

    assert len(runtime.list_results()) == 1
