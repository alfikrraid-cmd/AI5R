import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import RuntimeRegistry


def test_register_runtime():
    registry = RuntimeRegistry()

    runtime = object()

    registry.register(
        "company",
        runtime,
    )

    assert registry.count() == 1
    assert registry.exists("company")
    assert registry.get("company") is runtime


def test_unregister_runtime():
    registry = RuntimeRegistry()

    runtime = object()

    registry.register(
        "employee",
        runtime,
    )

    removed = registry.unregister("employee")

    assert removed is runtime
    assert registry.count() == 0
    assert registry.get("employee") is None


def test_list_runtime_ids():
    registry = RuntimeRegistry()

    registry.register("workflow", object())
    registry.register("company", object())
    registry.register("brain", object())

    assert registry.list_ids() == [
        "brain",
        "company",
        "workflow",
    ]


def test_list_all():
    registry = RuntimeRegistry()

    a = object()
    b = object()

    registry.register("a", a)
    registry.register("b", b)

    assert registry.list_all() == [a, b]


def test_clear_registry():
    registry = RuntimeRegistry()

    registry.register("one", object())
    registry.register("two", object())

    registry.clear()

    assert registry.count() == 0
