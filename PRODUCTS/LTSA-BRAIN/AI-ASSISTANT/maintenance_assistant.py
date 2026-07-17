"""Basic AI Assistant for OSA Maintenance v0.1 (MO-001 / BP-AI-ASSISTANT).

Reuses AI5R-SDK/BRAIN unmodified -- no BRAIN file is edited, extended, or
subclassed by this module. This is the first real product use of BRAIN,
consistent with ADR-002 (BRAIN is an AI5R-owned peer asset, consumed by a
product, never owned or modified by it) and ADR-003 (Capability/BRAIN
separation: BRAIN decides, Capability executes -- this module only calls
BRAIN's decision pipeline, it does not perform any action itself).

BRAIN's own Observation stage (AI5R-SDK/BRAIN/observation_engine.py) expects
a "reality" dict with an "object_type" key equal to "reality", and reads
measurements.vibration / measurements.temperature / findings for its signal
derivation -- exactly the shape AI5R-SDK/REALITY/reality_processing_station.py
already produces. This module builds that same shape from a maintenance
observation, so no new data contract is invented.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

# AI5R-SDK is a sibling of PRODUCTS/, not installed as a package -- add it to
# sys.path the same way pytest.ini's `pythonpath = AI5R-SDK` does for tests.
_AI5R_SDK_PATH = Path(__file__).resolve().parents[3] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from BRAIN.enterprise_cognitive_pipeline import EnterpriseCognitivePipeline  # noqa: E402


def build_reality(
    asset_code: str,
    findings_text: str,
    vibration: float | None = None,
    temperature: float | None = None,
    findings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a Reality-shaped dict, matching REALITY/reality_processing_station.py's output.

    `object_id` is required: BRAIN/observation_engine.py's ObservationEngine.observe()
    reads reality["object_id"] to populate ObservationObject.source_object_id, and
    BRAIN/understanding_engine.py's UnderstandingEngine.understand() raises
    ValueError("Observation must have source_object_id") if that ends up empty --
    discovered by actually running this module against real, unmodified BRAIN code,
    not assumed (see MO-001 Manufacturing Report).
    """
    return {
        "object_id": f"REALITY-{asset_code}-{uuid.uuid4().hex[:8]}",
        "object_type": "reality",
        "asset": asset_code,
        "raw_content": findings_text,
        "measurements": {
            "vibration": vibration,
            "temperature": temperature,
        },
        "findings": findings or [],
    }


def get_maintenance_recommendation(
    asset_code: str,
    findings_text: str,
    vibration: float | None = None,
    temperature: float | None = None,
    findings: list[str] | None = None,
) -> dict[str, Any]:
    """Run a maintenance observation through BRAIN's unmodified cognitive pipeline
    and return a recommendation. Reuses EnterpriseCognitivePipeline exactly as it
    already exists -- no BRAIN class is subclassed, wrapped, or altered here.
    """
    reality = build_reality(asset_code, findings_text, vibration, temperature, findings)

    pipeline = EnterpriseCognitivePipeline()
    result = pipeline.run(reality)

    decision = result["decision"]
    learning = result["learning"]

    return {
        "asset_code": asset_code,
        "selected_hypothesis": decision.selected_hypothesis,
        "rationale": decision.rationale,
        "recommendation": learning.lesson,
        "confidence_delta": learning.confidence_delta,
        "knowledge_update_required": learning.knowledge_update_required,
    }


if __name__ == "__main__":
    example = get_maintenance_recommendation(
        asset_code="P-101",
        findings_text="Vibration 11.2 mm/s, bearing temperature 92 C, seal leakage observed",
        vibration=11.2,
        temperature=92,
        findings=["seal_leakage", "bearing"],
    )
    import json

    print(json.dumps(example, indent=2))
