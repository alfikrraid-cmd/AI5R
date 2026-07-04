import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from PRODUCTS.LTSA_BRAIN.knowledge_matching_engine import KnowledgeMatchingEngine
from PRODUCTS.LTSA_BRAIN.recommendation_engine import RecommendationEngine


def test_recommendation_engine_generates_actionable_recommendation():
    processed = {
        "asset": "P-101",
        "findings": [
            "seal_leakage",
            "bearing_issue",
        ],
        "measurements": {
            "vibration": 11.2,
            "temperature": 92,
        },
    }

    matcher = KnowledgeMatchingEngine()
    matched = matcher.match(processed)

    engine = RecommendationEngine()
    result = engine.recommend(
        asset=processed["asset"],
        processed=processed,
        matched_knowledge=matched,
    )

    assert result["asset"] == "P-101"
    assert result["priority"] == "CRITICAL"
    assert "Replace bearing" in result["recommendation"]
    assert "Replace seal" in result["recommendation"]
    assert "Perform vibration analysis" in result["recommendation"]
    assert "Schedule maintenance shutdown within 24 hours" in result["recommendation"]
    assert result["status"] == "recommended"

    print("LTSA-008 Recommendation Engine OK")


if __name__ == "__main__":
    test_recommendation_engine_generates_actionable_recommendation()
