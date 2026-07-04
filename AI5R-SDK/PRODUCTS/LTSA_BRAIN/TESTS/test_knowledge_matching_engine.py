import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from PRODUCTS.LTSA_BRAIN.knowledge_matching_engine import KnowledgeMatchingEngine


def test_knowledge_matching_engine_matches_combined_findings():
    engine = KnowledgeMatchingEngine()

    result = engine.match({
        "findings": [
            "seal_leakage",
            "bearing_issue",
        ]
    })

    assert result["priority"] == "CRITICAL"
    assert "Replace bearing" in result["recommendation"]
    assert "Replace seal" in result["recommendation"]

    print("LTSA-007 Knowledge Matching Engine OK")


if __name__ == "__main__":
    test_knowledge_matching_engine_matches_combined_findings()
