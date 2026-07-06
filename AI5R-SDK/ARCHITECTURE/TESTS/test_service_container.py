import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import ServiceContainer


def test_register_instance():
    container = ServiceContainer()

    obj = object()

    container.register_instance(
        "memory",
        obj,
    )

    assert container.resolve("memory") is obj


def test_register_factory_singleton():
    container = ServiceContainer()

    counter = {"value": 0}

    def factory():
        counter["value"] += 1
        return {"id": counter["value"]}

    container.register_factory(
        "knowledge",
        factory,
    )

    first = container.resolve("knowledge")
    second = container.resolve("knowledge")

    assert first is second
    assert counter["value"] == 1


def test_registered_services():
    container = ServiceContainer()

    container.register_instance(
        "memory",
        object(),
    )

    container.register_factory(
        "brain",
        lambda: object(),
    )

    assert container.registered_services() == [
        "brain",
        "memory",
    ]


def test_unknown_service():
    container = ServiceContainer()

    try:
        container.resolve("missing")
        assert False
    except KeyError:
        pass
