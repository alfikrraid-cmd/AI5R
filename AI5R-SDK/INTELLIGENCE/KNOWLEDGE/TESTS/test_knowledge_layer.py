import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.LAYER.knowledge_layer import (
    KnowledgeLayer,
)


def test_manifest_contains_layer_name():
    manifest = KnowledgeLayer.manifest()

    assert manifest["layer"] == "Knowledge"
    assert manifest["version"] == "1.0.0"


def test_manifest_contains_service():
    manifest = KnowledgeLayer.manifest()

    assert "KnowledgeService" in manifest["services"]


def test_manifest_contains_pipeline():
    manifest = KnowledgeLayer.manifest()

    assert "KnowledgeProcessingPipeline" in manifest["pipelines"]


def test_manifest_contains_object():
    manifest = KnowledgeLayer.manifest()

    assert "KnowledgeObject" in manifest["objects"]


def test_manifest_contains_capabilities():
    assert KnowledgeLayer.supports("classification")
    assert KnowledgeLayer.supports("processing")
    assert KnowledgeLayer.supports("service_runtime")


def test_component_count():
    assert KnowledgeLayer.component_count() >= 7
