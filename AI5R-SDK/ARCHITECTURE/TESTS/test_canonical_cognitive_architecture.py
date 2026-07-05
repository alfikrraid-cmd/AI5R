import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.canonical_cognitive_architecture import (
    CanonicalCognitiveArchitecture,
)


def test_architecture_contains_nine_layers():
    assert len(CanonicalCognitiveArchitecture.all_layers()) == 9


def test_layer_codes_are_unique():
    codes = CanonicalCognitiveArchitecture.layer_codes()

    assert len(codes) == len(set(codes))


def test_knowledge_layer_exists():
    layer = CanonicalCognitiveArchitecture.find("KNW")

    assert layer is not None
    assert layer.name == "Knowledge"
    assert "classification" in layer.responsibilities
    assert "graph" in layer.responsibilities


def test_cognition_layer_exists():
    layer = CanonicalCognitiveArchitecture.find("COG")

    assert layer is not None
    assert "reasoning" in layer.responsibilities
    assert "planning" in layer.responsibilities


def test_learning_layer_exists():
    layer = CanonicalCognitiveArchitecture.find("LRN")

    assert layer is not None
    assert "innovation" in layer.responsibilities
