import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.exceptions import ModelNotRegisteredError
from AI_RUNTIME.ROUTER.model_registry import ModelDescriptor, ModelRegistry


def _model(name="gpt-4o-mini", provider="OPENAI", capabilities=frozenset({"chat"})):
    return ModelDescriptor(model_name=name, provider_name=provider, capabilities=capabilities)


def test_register_and_get():
    registry = ModelRegistry()
    model = _model()

    registry.register(model)

    assert registry.get("gpt-4o-mini") is model


def test_get_unknown_model_raises():
    registry = ModelRegistry()

    with pytest.raises(ModelNotRegisteredError):
        registry.get("unknown-model")


def test_unregister_removes_model():
    registry = ModelRegistry()
    registry.register(_model())

    registry.unregister("gpt-4o-mini")

    with pytest.raises(ModelNotRegisteredError):
        registry.get("gpt-4o-mini")


def test_unregister_unknown_model_raises():
    registry = ModelRegistry()

    with pytest.raises(ModelNotRegisteredError):
        registry.unregister("unknown-model")


def test_list_all():
    registry = ModelRegistry()
    model = _model()
    registry.register(model)

    assert registry.list_all() == [model]


def test_list_by_provider():
    registry = ModelRegistry()
    openai_model = _model(name="gpt-4o-mini", provider="OPENAI")
    claude_model = _model(name="claude-sonnet", provider="CLAUDE")
    registry.register(openai_model)
    registry.register(claude_model)

    assert registry.list_by_provider("OPENAI") == [openai_model]


def test_list_by_capability():
    registry = ModelRegistry()
    vision_model = _model(name="gpt-4o", provider="OPENAI", capabilities=frozenset({"chat", "vision"}))
    chat_model = _model(name="gpt-4o-mini", provider="OPENAI", capabilities=frozenset({"chat"}))
    registry.register(vision_model)
    registry.register(chat_model)

    assert registry.list_by_capability("vision") == [vision_model]
