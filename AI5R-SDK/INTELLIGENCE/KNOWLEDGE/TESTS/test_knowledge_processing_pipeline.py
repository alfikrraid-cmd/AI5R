import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.knowledge_processing_pipeline import (
    KnowledgeProcessingPipeline,
)


def test_pipeline_processes_knowledge_object():
    pipeline = KnowledgeProcessingPipeline()

    knowledge = KnowledgeObject(
        knowledge_id="KO-P001",
        summary="UMKM needs pricing strategy to increase revenue",
        metadata={
            "impact": 0.9,
            "urgency": 0.8,
            "actionability": 0.9,
        },
    )

    knowledge.impact = 0.9
    knowledge.urgency = 0.8
    knowledge.actionability = 0.9

    result = pipeline.process(knowledge)

    processed = result.knowledge_object

    assert processed.classification["domain"] == "business"
    assert processed.priority["priority_level"] in ["HIGH", "CRITICAL"]
    assert "classification" in result.stages
    assert "prioritization" in result.stages


def test_pipeline_accepts_dict_input():
    pipeline = KnowledgeProcessingPipeline()

    result = pipeline.process({
        "knowledge_id": "KO-P002",
        "summary": "Build python module and unit test for API workflow",
        "impact": 0.8,
        "urgency": 0.7,
        "actionability": 0.9,
    })

    processed = result.knowledge_object

    assert isinstance(processed, KnowledgeObject)
    assert processed.classification["domain"] == "technical"
    assert processed.priority["priority_score"] >= 0.5


def test_pipeline_process_many():
    pipeline = KnowledgeProcessingPipeline()

    results = pipeline.process_many([
        {
            "knowledge_id": "KO-P003",
            "summary": "School curriculum needs assessment plan",
        },
        {
            "knowledge_id": "KO-P004",
            "summary": "Factory pipeline requires registry integration",
        },
    ])

    assert len(results) == 2
    assert results[0].knowledge_object.classification["domain"] == "education"
    assert results[1].knowledge_object.classification["domain"] == "operation"


def test_pipeline_rejects_empty_many():
    pipeline = KnowledgeProcessingPipeline()

    try:
        pipeline.process_many([])
        assert False
    except ValueError as error:
        assert "knowledge_objects are required" in str(error)

from FOUNDATION.pipeline_contract import PipelineContract


def test_knowledge_processing_pipeline_implements_contract():
    pipeline = KnowledgeProcessingPipeline()

    assert isinstance(pipeline, PipelineContract)


def test_knowledge_processing_pipeline_execute_delegates_to_process():
    pipeline = KnowledgeProcessingPipeline()

    result = pipeline.execute({
        "knowledge_id": "KO-P005",
        "summary": "UMKM pricing strategy improves revenue",
    })

    assert result.knowledge_object.classification["domain"] == "business"
    assert "classification" in result.stages
