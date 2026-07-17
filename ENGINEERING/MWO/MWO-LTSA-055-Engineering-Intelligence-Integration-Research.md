# MWO-LTSA-055 — Engineering Intelligence Integration — WP-000 Research

Status: **WP-000 APPROVED.** Research PASS, Architecture PASS. `MWO-LTSA-051`'s deferral stands, unchanged: no Knowledge Engine, no Recommendation Engine implementation authorized. Knowledge Manufacturing (Links 1–2) remains a future MWO, scheduled after LTSA v1.0. No implementation performed.
Type: Manufacturing Work Order (Research)
Role: Implementation Engineer
Architecture: FROZEN — nothing proposed here changes it; this report extends `MWO-LTSA-051`'s already Chief-approved finding by one further hop, using only already-approved concepts (ADR-002's cognitive loop, `KNOWLEDGE/` KF-005, `CAPABILITY/` CP-008, `BRAIN/`)
Scope: Research only. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, or Runtime file modified in producing this document.

---

## Executive Summary

`MWO-LTSA-051` (Chief-approved, Research/Architecture/Knowledge Model all PASS) already established and confirmed one link in this chain: **`LearningObject → KnowledgeObject`** is a real gap — `LearningObject` is produced today, for real, by a genuinely executed pipeline (MO-001's Basic AI Assistant); `KnowledgeObject` persistence never happens, because `KNOWLEDGE.KnowledgeIngestionEngine` is never called by anything. That finding is re-verified here (nothing in the repository has changed it since `051`) and is not re-litigated.

**This research's own finding, extending `051` one hop further:** the chain requested — `LearningObject → KnowledgeObject → Engineering Recommendation` — actually has **two** missing links, not one, and the third node (**Engineering Recommendation**) is a false gap in one specific sense: **Engineering Recommendation already exists today, for real, executed code** (`PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py:get_maintenance_recommendation()`). What's missing is not the *existence* of a recommendation — it's making that recommendation **knowledge-informed**: today it is a stateless, one-shot output of a single pipeline run, with no memory of any prior run and no way to improve as more evidence accumulates. That is a direct, unavoidable consequence of the same gap `051` found: if `LearningObject`s are never persisted as `KnowledgeObject`s, there is nothing for a later recommendation to draw on.

---

## 1. Current Flow (grounded, re-verified, unchanged since `MWO-LTSA-051`)

```
Inspection / maintenance observation (a plain Python dict, Reality-shaped)
        │  built by maintenance_assistant.build_reality()
        ▼
BRAIN.EnterpriseCognitivePipeline.run(reality)      ← real, executed, unmodified BRAIN
        │
        ├─► ObservationEngine.observe()   → ObservationObject
        ├─► UnderstandingEngine.understand() → hypotheses
        ├─► DecisionEngine (produces `decision`: selected_hypothesis, rationale)
        └─► LearningEngine (produces `learning`: a real LearningObject)
        ▼
maintenance_assistant.get_maintenance_recommendation() returns:
{
  "asset_code": ..., "selected_hypothesis": ..., "rationale": ...,
  "recommendation": learning.lesson,          ← THIS is "Engineering Recommendation" today
  "confidence_delta": learning.confidence_delta,
  "knowledge_update_required": learning.knowledge_update_required
}
```

This is real, tested, and (per MO-001's own Manufacturing Report, cited by `051`) actually executed — not aspirational. `learning.knowledge_update_required` is even a boolean flag the `LearningObject` itself carries, explicitly signaling "this outcome should update Knowledge" — and nothing downstream ever reads that flag. It is computed and discarded on every single call.

**Confirmed by direct code read this pass:** `AI5R-SDK/CAPABILITY/capability_validation_engine.py`'s `validate()` checks only that `CapabilityObject.required_knowledge_ids` is *non-empty* (a warning, not an error, if missing) — it does not resolve those IDs against anything. `ADR-002`'s own Migration Step 1 ("`CapabilityValidationEngine` resolves `required_knowledge_ids` against `KNOWLEDGE/`'s existing `KnowledgeRegistry`") is **not implemented**, confirming the loop is disconnected at this point too, not only at the Learning→Knowledge point `051` already found.

## 2. The Missing Link(s)

**Link 1 — `LearningObject → KnowledgeObject`** (re-confirmed, not re-researched): `KNOWLEDGE.KnowledgeIngestionEngine` exists (`AI5R-SDK/KNOWLEDGE/knowledge_ingestion_engine.py`) but nothing in the repository ever calls it with a `LearningObject`. `051`'s finding stands unchanged.

**Link 2 — `KnowledgeObject → (informs) → Engineering Recommendation`** — this is this research's own extension. Per `ADR-002` §2's target loop, this link is not direct; it routes through Capability:

```
KnowledgeObject (persisted, per Link 1, once built)
        │
CapabilityValidationEngine resolves CapabilityObject.required_knowledge_ids
   against KnowledgeRegistry                          ← ADR-002 Step 1, confirmed NOT implemented
        │
CapabilityRuntime's engine-injection point supplies
   EnterpriseBrainRuntime in place of default CapabilityEngine  ← ADR-002 Step 2, confirmed NOT implemented
        │
BRAIN's reasoning for a *future* Inspection is now informed by
   accumulated Knowledge, not run cold each time
        │
        ▼
Engineering Recommendation (already real today, per §1) becomes
   knowledge-informed rather than stateless
```

**So "the missing link to Engineering Recommendation" is not one link — it is Links 1 and 2 of ADR-002's own already-specified Migration Strategy (Steps 1, 2, and 5), applied to this domain, neither of which has been implemented.** Nothing new needs to be invented; two already-specified, already-approved migration steps need to be implemented, in the order ADR-002 itself already sequences them (§3: Steps 1, 3, 4 before Step 2, then Step 5).

## 3. Integration Points

| Point | File | Status |
|---|---|---|
| BRAIN consumption (Reality → decision/learning) | `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py` | **Real, executed** — the only production integration point that exists today |
| Learning → Knowledge ingestion | `AI5R-SDK/KNOWLEDGE/knowledge_ingestion_engine.py` | Exists, never called (Link 1) |
| Knowledge → Capability validation | `AI5R-SDK/CAPABILITY/capability_validation_engine.py` | Exists, checks presence only, does not resolve (Link 2, ADR-002 Step 1) |
| Capability → BRAIN reasoning injection | `AI5R-SDK/CAPABILITY/capability_runtime.py`'s `engine=None` constructor param | Exists as a seam (per ADR-002 §3 Step 2's own description), not yet used to inject `EnterpriseBrainRuntime` |
| AI Workforce → Capability execution | `OSA/CAPABILITY_RESOLVER` | Hardcoded keyword dict today (ADR-002 §1), not yet reading real `CapabilityRegistry` |

Every integration point above already exists as code; none needs to be newly designed. What's missing is exclusively the *wiring between* them — exactly ADR-002's own characterization ("each step reuses an existing component; none invents a new runtime, registry, or engine").

## 4. "Engineering Intelligence" and "Engineering Recommendation" — where these terms come from

`AI5R-SDK/ARCHITECTURE/DOCS/AX-302-ENTERPRISE-INTELLIGENCE-SUITE.md` names **"Engineering Intelligence"** as one of several **Domain Packs** extending an "Enterprise Foundation," under a stated **Intelligence Principle**: *"Every module shall Observe, Diagnose, Recommend, Improve, Learn."* This is a vision document (no implementation detail, no citations to concrete code), but it is the only place in the repository that names "Engineering Intelligence" and "Recommend" as formal, related concepts — grounding this MWO's own title and the term "Engineering Recommendation" in existing (if aspirational) architecture vocabulary, not inventing new terminology. Mapped onto what actually exists: **Observe** = `ObservationEngine`, **Diagnose** = `UnderstandingEngine`/`DecisionEngine`, **Recommend** = `learning.lesson` surfaced by `maintenance_assistant.py` today, **Improve/Learn** = the two missing links (§2) that would let Recommend get better over time instead of resetting on every call.

## 5. LTSA Impact

- `PRODUCTS/LTSA-BRAIN/product.manifest.json`'s `ai_assistant` module entry (currently `"partial"`, description already notes BRAIN's `UnderstandingEngine` gap fixed during MO-001) would need its own note added once/if this loop closes — not done here.
- `MWO-LTSA-030`'s own worked Copilot Example (*"Pump 211-P-1 requires Seal 2-1/8"... Recommended: Purchase additional stock"*) is exactly the shape of output `get_maintenance_recommendation()` already produces — this MWO's two missing links are precisely what would let that recommendation improve as more Installation/Inspection/Maintenance History events (this session's own `MWO-LTSA-030`/`MO-001` tables) accumulate, rather than being computed fresh, context-free, every time.
- Every canonical LTSA-BRAIN table this session and prior sessions manufactured (`seal_registry`, `seal_stock`, `seal_pump_compatibility`, `maintenance_history`, `work_order`, `knowledge_source_registry`, `acquisition_job`, etc.) is a candidate **source of Reality-shaped input** to this loop, but none is currently wired to it — `maintenance_assistant.py`'s `build_reality()` is called with hand-constructed test data today (see its own `__main__` block), not with a real query against any of these tables.
- `MWO-LTSA-051`'s own explicit decision stands and is not overridden here: *"No Knowledge Engine is authorized at this time... Knowledge Manufacturing... becomes a future MWO, scheduled after LTSA v1.0."* This research does not propose changing that sequencing — it documents one hop further along the same deferred chain, for the same future MWO to consume.

---

## Open Questions (for a future Architecture Decision — not decided here)

1. Should Link 1 (Learning→Knowledge) and Link 2 (Knowledge→Capability→BRAIN) be implemented as one combined future MWO, or two separately-approved ones, matching ADR-002's own step-by-step, independently-approvable sequencing?
2. What would actually populate `LearningObject`s worth persisting at LTSA-BRAIN scale — is `maintenance_assistant.py` (currently a demo/example entrypoint) expected to become a real, scheduled or event-triggered process reading from `maintenance_history`/`work_order`, or does that remain out of scope for the Knowledge Manufacturing MWO this defers to?
3. Does "Engineering Recommendation" as a deliverable mean surfacing `learning.lesson` through some new LTSA-BRAIN-facing interface (a workflow, an API), or is the recommendation dict `maintenance_assistant.py` already returns considered sufficient once knowledge-informed?

---

## Deliverables (this document only)

- This WP-000 research document, citing every claim to a direct file/code read, and explicitly building on (not duplicating) `MWO-LTSA-051`'s own Chief-approved finding.
- No code, schema, or build pack. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, or Runtime file modified.

## Definition of Done (for this research)

- Current flow described and grounded in real, executed code (`maintenance_assistant.py`). **Met.**
- Missing link(s) identified — confirmed as two, not one, both already specified by `ADR-002`'s own Migration Strategy, neither newly invented. **Met.**
- Integration points enumerated with file-level citations and current status (real / exists-unused / partial). **Met.**
- LTSA impact stated, tied to this session's own manufactured tables and `MWO-LTSA-030`'s Copilot Example. **Met.**
- `MWO-LTSA-051`'s prior finding and deferral decision preserved, not overridden. **Met.**

---

Research only. Stopping here after WP-000, as instructed. Awaiting approval.
