import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EVIDENCE.evidence_object import EvidenceObject


def test_evidence_object():

    evidence = EvidenceObject(
        evidence_name="Campaign A Performance",
        source_type="MEMORY",
        source_ids=["MEM-001", "MEM-002"],
        sample_size=100,
        success_count=79,
        failure_count=21,
        confidence_score=0.79,
        measurement_period="2026-Q3",
        metrics={
            "conversion_rate": 0.12,
            "roi": 1.8,
        },
        supporting_artifacts=[
            "ART-001",
        ],
        metadata={
            "owner": "AI5R",
        },
    )

    assert evidence.object_type == "EVIDENCE"
    assert evidence.status == "COLLECTED"
    assert evidence.evidence_name == "Campaign A Performance"
    assert evidence.sample_size == 100
    assert evidence.success_count == 79
    assert evidence.failure_count == 21
    assert evidence.confidence_score == 0.79
    assert evidence.evidence_id.startswith("EVD-")
