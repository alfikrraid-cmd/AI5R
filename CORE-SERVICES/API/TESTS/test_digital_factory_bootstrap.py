import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import API.digital_factory_bootstrap as digital_factory_bootstrap
from API.digital_factory_bootstrap import get_digital_factory


def test_get_digital_factory_returns_same_instance():
    first = get_digital_factory()
    second = get_digital_factory()

    assert first is second


def test_get_digital_factory_returns_valid_factory():
    factory = get_digital_factory()

    assert factory.validate() is True
    assert factory.factory_id == "DF-001"
    assert factory.factory_name == "AI5R Digital Factory"


def test_get_digital_factory_starts_with_empty_registry(monkeypatch):
    # A freshly bootstrapped factory starts empty. Reset the module-level
    # singleton for this test only, so the assertion holds regardless of
    # what other, legitimately-registering test files already ran in this
    # same pytest session (the singleton is process-wide by design).
    monkeypatch.setattr(digital_factory_bootstrap, "_digital_factory", None)

    factory = get_digital_factory()

    assert factory.registry.recipe_count() == 0
    assert factory.registry.line_count() == 0
