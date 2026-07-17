# BP-AI-ASSISTANT — Basic AI Assistant

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED

The Basic AI Assistant required module, manufactured by reusing `AI5R-SDK/BRAIN` exactly as it already exists -- no BRAIN file is modified, subclassed, or wrapped. This is the first real product use of BRAIN in this repository, consistent with:

- **ADR-002** (The Role of BRAIN in OSA): BRAIN is an AI5R-owned peer asset, consumed by a product, never owned by it.
- **ADR-003** (Capability as Universal Execution Layer): BRAIN decides; this module only asks BRAIN for a decision, it does not itself perform any maintenance action.

## Contents

- `maintenance_assistant.py` — `build_reality()` constructs a Reality-shaped dict matching `AI5R-SDK/REALITY/reality_processing_station.py`'s output shape; `get_maintenance_recommendation()` runs it through `BRAIN.enterprise_cognitive_pipeline.EnterpriseCognitivePipeline` (unmodified) and extracts a recommendation from the resulting `DecisionObject` and `LearningObject`.
- `TEST/test_maintenance_assistant.py` — unlike every other module in this order, this test has no external database dependency (BRAIN's pipeline is pure Python) and was actually executed, not just structurally validated — see the MO-001 Manufacturing Report for the real run's output.

## Known Limitation

BRAIN's own Outcome stage (per the MWO-OSA-006 audit) always marks every task completed, so `knowledge_update_required` will effectively always be `false` when driven end-to-end through this assistant — the same limitation documented in ADR-002's Migration Strategy. This is inherited from BRAIN as-is, not introduced by this module, and BRAIN was not modified to work around it.
