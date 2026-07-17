**Knowledge ID:** MR-KP-003
**Title:** AI5R-SDK/BRAIN's public pipeline interface is genuinely consumable by a product with zero modification
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001's Basic AI Assistant module called `AI5R-SDK/BRAIN/enterprise_cognitive_pipeline.py::EnterpriseCognitivePipeline.run(reality_dict)` directly, with no change to any BRAIN file. This is the first confirmed case, across this Factory's engagement, of BRAIN being consumed by a product exactly as ADR-002/ADR-003 describe (BRAIN as an AI5R-owned peer asset, consumed not owned; BRAIN decides, the product does not redesign it). A real defect was found and fixed entirely within the consuming module's own input-construction code, without touching BRAIN.
**Recommendation:** Future products needing cognitive/reasoning capability should consume `BRAIN.enterprise_cognitive_pipeline.EnterpriseCognitivePipeline.run()` directly, the same way MO-001 did, rather than building a parallel reasoning mechanism. Any input-shape mismatch discovered should be fixed in the consuming module, not by modifying BRAIN.
**Reuse Scope:** Any future AI5R product requiring cognitive/reasoning capability (per ADR-002's stated reusability intent: Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath, and others).
