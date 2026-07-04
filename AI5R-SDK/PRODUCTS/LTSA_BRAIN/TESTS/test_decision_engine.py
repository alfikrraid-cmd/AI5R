import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from PRODUCTS.LTSA_BRAIN.knowledge_matching_engine import KnowledgeMatchingEngine
from PRODUCTS.LTSA_BRAIN.recommendation_engine import RecommendationEngine
from PRODUCTS.LTSA_BRAIN.decision_engine import DecisionEngine


def test_decision_engine_generates_critical_decision():
    reality = {
        "source_type": "pump_report",
        "source_name": "sample.txt",
    }

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

    knowledge = KnowledgeMatchingEngine()
    recommender = RecommendationEngine()
    decision_engine = DecisionEngine()

    matched_knowledge = knowledge.match(processed)

    recommendation = recommender.recommend(
        reality,
        processed,
        matched_knowledge,
    )

    result = decision_engine.decide(recommendation)

    assert result["priority"] == "CRITICAL"
    assert result["decision"] == "IMMEDIATE_MAINTENANCE_REQUIRED"
    assert result["execution_mode"] == "urgent"

    print("LTSA-009 Decision Engine OK")


if __name__ == "__main__":
    test_decision_engine_generates_critical_decision()
