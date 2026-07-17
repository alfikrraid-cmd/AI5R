# ADR-002 — The Role of BRAIN in OSA

## Status

Proposed

## Context

Six prior investigations (MWO-OSA-001 through 006, this session) established the repository facts this ADR builds on. The Chief Architect clarified that an ADR's purpose is to state the target architecture the repository evolves toward, not merely to describe its current state. This ADR is structured accordingly: **Section 1 describes what exists today; Section 2 states what AI5R's architecture is intended to be, per Chief Architect decision; Section 3 describes how to get from one to the other.** These are kept in strictly separate sections and must not be read as interchangeable.

---

## 1. Current Repository Architecture (Descriptive)

This section states only what exists today, as evidence. It contains no "should," no target, no recommendation.

- **OSA** is the live, wired chain: `AI5R_KERNEL/ai5r.py` → `PRODUCT_RUNTIME` → `OSA/RUNTIME_PIPELINE` → `OSA/CAPABILITY_RESOLVER` → `OSA/DIGITAL_EMPLOYEE_ORCHESTRATOR` → `OSA/EXECUTION_DISPATCHER` → `OSA/REFLECTION_ENGINE` → `OSA/MEMORY_LEARNING_ENGINE`.
- **AI Workforce** exists today as `OSA/CAPABILITY_RESOLVER` (a hardcoded keyword-to-capability-id dict) + `OSA/DIGITAL_EMPLOYEE_ORCHESTRATOR` (flat, single-tier assignment). The Blueprint's six-level hierarchy exists only as documentation, not code.
- **Knowledge** (`KNOWLEDGE/`, frozen spec `KF-005`) and **Capability** (`CAPABILITY/`, frozen spec `CP-008`) are each real, internally coherent, but orphaned — no code connects Knowledge to Capability, and no code connects Capability to AI Workforce.
- **BRAIN** is currently independent. It has no production relationship with OSA, Knowledge, or Capability. It contains a complete Observation→Learning cognitive pipeline. It owns its own Runtime, Registry, and Manufacturing Station. Its only external reference anywhere in the repository is from `MEMORY/TESTS/*.py` — test code, not production code.
- **Execution → Reflection → Learning** is live and wired, with one known gap: `MemoryLearningEngine.learn()` is called unconditionally; `.ignore()` is never reached.
- **Reality → Warehouse → Experience → Memory (top-level)** is a documented ordering with no confirmed cross-package imports connecting the four packages to each other.
- **Evolution** (Learning feeding back into Specification) has no implementation anywhere in the repository.

These are the accepted facts from MWO-OSA-001 through 006. Nothing above is altered by this ADR.

---

## 2. Target AI5R Architecture (Normative)

This section states intent, per Chief Architect decision, consistent with the frozen Blueprint's layered structure (Vol. II, Ch.1: AI5R → Digital Factory → OSA → OSA Systems → Enterprise Objects → AI Workforce → OSA Instance) and its Capability definition (Vol. II, Ch.6). It elaborates that structure at engineering resolution; it does not alter any frozen Blueprint text.

**Ownership:**

- **AI5R owns four peer strategic assets: the Knowledge Foundation, the Capability Foundation, BRAIN, and OSA.** None of these is subordinate to another in ownership terms — they sit as peers directly under AI5R, not in an ownership chain running through OSA.
- **OSA consumes BRAIN. OSA does not own BRAIN.** This distinction is intentional: BRAIN must remain reusable by future AI5R products beyond OSA — Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath, and any future AI5R product. If OSA owned BRAIN, that reusability would be architecturally foreclosed — a future product could not draw on BRAIN's reasoning without going through OSA first.

**Role definitions:**

- **BRAIN is the Enterprise Cognitive Processor** — an AI5R-owned, product-agnostic reasoning mechanism that turns observation into decision, available to OSA and to any other AI5R product.
- **Knowledge is the Enterprise Knowledge Base** — what AI5R knows, likewise owned at the AI5R level, not scoped to any one product.
- **Capability is Executable Knowledge** — the registered, invocable expression of that knowledge as action, consistent with Vol. II Ch.6's definition of Capability as "a defined, reusable unit of business function."

**The intended cognitive loop, as OSA specifically consumes AI5R's peer assets:**

```
                    AI5R
                     │
      ┌──────────────┼──────────────┬──────────────┐
      ▼              ▼              ▼              ▼
  Knowledge      Capability       BRAIN            OSA
 (Foundation)    (Foundation)  (Cognitive        (consumes
                                Processor)      Knowledge,
      │              │              │           Capability,
      └──(feeds)──►  │              │           and BRAIN)
                     └──(feeds)──►  │
                                    │
                                    ▼
                              AI Workforce
                         (inside OSA; executes Capability
                          using reasoning BRAIN produces)
                                    │
                                    ▼
                                Execution
                           (performs the work)
                                    │
                                    ▼
                                Reflection
                          (evaluates the work)
                                    │
                                    ▼
                                 Learning
                          (improves Knowledge) ───┐
                                                    │
        ┌───────────────────────────────────────────┘
        ▼
   Knowledge (improved) ──(improves)──► Capability ──(improves)──► future reasoning in BRAIN
```

This is a **closed loop, not a one-way pipeline**: Learning improves Knowledge; improved Knowledge improves Capability; improved Capability improves BRAIN's future reasoning. Knowledge, Capability, and BRAIN sit at the AI5R level, available to be fed by and to improve from *any* AI5R product's runtime — OSA is the first and, today, only consumer, not the owner. This is the concrete, engineering-level elaboration of the Blueprint's Continuous Evolution principle (Vol. I Ch.5; Vol. II Ch.2/9) — it gives that principle a specific shape without conflicting with anything frozen in Volumes I or II; it is additive engineering detail, not a Blueprint change.

**AI Workforce's target role** (AI Workforce itself remains inside OSA, per Vol. II Ch.7) shifts from today's flat keyword-matcher to a genuine consumer of BRAIN's reasoning, drawn from AI5R's shared BRAIN asset rather than an OSA-private copy of it: it executes a Capability, and the reasoning behind *which* capability and *how* comes from BRAIN.

---

## 3. Migration Strategy (Step-by-Step Evolution)

Every step below reuses an existing component; none invents a new runtime, registry, or engine. Each step is independently approvable, independently verifiable, and minimizes risk by touching the smallest possible surface first.

**Step 1 — Wire Knowledge → Capability (validation only).** `CapabilityValidationEngine` resolves `CapabilityObject.required_knowledge_ids` against `KNOWLEDGE/`'s existing `KnowledgeRegistry`. Zero production risk — both packages are currently orphaned, so this touches no live path.

**Step 2 — Wire OSA's consumption of BRAIN.** `CapabilityRuntime` already accepts an injected `engine` (its constructor: `engine=None` defaults to `CapabilityEngine()`). For capabilities flagged as reasoning-dependent, OSA's capability execution path injects `EnterpriseBrainRuntime` in place of the default `CapabilityEngine` — reusing `CapabilityRuntime`'s existing dependency-injection point rather than creating a new integration mechanism, and without relocating BRAIN into OSA's own package tree. This is the step that makes BRAIN OSA-*consumed* in practice, not merely declared as a peer asset in principle — and because the injection point belongs to `CapabilityRuntime`, not to BRAIN itself, any other future AI5R product could equally inject `EnterpriseBrainRuntime` into its own execution path without modification to BRAIN.

**Step 3 — Wire AI Workforce → Capability.** Replace `CapabilityResolver`'s hardcoded dict with real `CapabilityRegistry.exists()`/`.get()` calls, exactly as already designed in MWO-OSA-002 Deliverable 1. Once Step 2 is in place, this transitively makes AI Workforce's assignments BRAIN-informed, with no additional wiring required — a natural consequence of Steps 1–3, not a fourth integration point.

**Step 4 — Fix Reflection → Learning branching.** `RuntimePipeline` should call `.ignore()` for FAILED reflections instead of unconditional `.learn()`. Smallest possible diff, already fully scoped in MWO-OSA-004.

**Step 5 — Close Learning → Knowledge.** Feed a `LearnedMemory` (or BRAIN's own `LearningObject`) into `KNOWLEDGE/`'s existing `KnowledgeIngestionEngine`, reusing its current ingest path rather than building a new one. This is the first concrete implementation of the "Learning improves Knowledge" loop segment, and — because Knowledge is an AI5R-level asset, not OSA-private — this closes the loop for every future consumer of Knowledge, not only OSA.

**Step 6 — Close Knowledge → Capability as an ongoing loop, not a one-time check.** Extend Step 1's validation call to re-run when Knowledge changes, using the same existing `CapabilityValidationEngine`/`KnowledgeRegistry` methods — no new mechanism, just a different trigger.

**Sequencing notes:**

- BRAIN's own internal gap (its Outcome stage cannot structurally reach the Learning failure branch, per MWO-OSA-006) should be addressed before or during Step 2 — integrating a reasoning engine that can't signal failure would silently understate risk in AI Workforce's decisions, and since BRAIN is AI5R-owned and reusable, this fix benefits every future consumer, not only OSA.
- Steps 1–4 touch orphaned or narrowly-scoped code; Step 2 is the first to make BRAIN production-relevant and therefore carries the most risk in this sequence — it should not be attempted before Steps 1, 3, and 4 have independently validated the smaller integration pattern.
- The earlier `Reality → Warehouse → Experience → Memory(top)` segment remains outside this migration strategy's resolved scope — it is not part of the Chief's stated target architecture for this ADR and remains a separately deferred item (per MWO-OSA-004's roadmap item 4).

None of the six steps above are approved for implementation by this ADR — they are the sequence a future, separately-approved MWO would follow.

---

## Consequences

### Positive

- Gives BRAIN a defined destination — an AI5R-owned Enterprise Cognitive Processor, consumed by OSA and reusable by future AI5R products — instead of leaving it permanently classified as merely independent.
- The migration strategy reuses `CapabilityRuntime`'s existing engine-injection point (Step 2) rather than requiring a new integration mechanism — consistent with "prefer reuse over redesign."
- Explicitly preserves BRAIN's, Knowledge's, and Capability's availability to future AI5R products (Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath, and others) by keeping them peer assets under AI5R rather than subordinated into OSA.
- Clearly separates fact from intent, so future MWOs can cite Section 1 as ground truth and Section 2 as the direction to build toward, without conflating the two.

### Negative

- The target architecture (Section 2) is not yet validated by any working code — adopting it as canonical commits to a direction, not a proof.
- Step 2 of the migration (OSA consuming BRAIN) is the first point where BRAIN becomes production-relevant, and therefore the first point where its known internal gap (Outcome-stage failure path) becomes a real operational risk rather than a dormant one.
- The Reality→Warehouse→Experience→Memory segment remains unresolved and outside this ADR's migration scope — a future ADR or MWO will be needed to decide its fate.

## Alternatives Considered

- **Make OSA own BRAIN outright** — rejected. This was the initial draft's position, but it would foreclose BRAIN's reuse by future AI5R products that have no relationship to OSA (Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath). AI5R's actual strategic interest is in BRAIN as a reusable, product-agnostic cognitive engine, not as an OSA-internal component.
- **Leave BRAIN permanently classified as independent** — rejected per Chief direction: an ADR must state target architecture, not only current state.
- **Invent a new "Reasoning Runtime" component to bridge Capability and BRAIN** — rejected; `CapabilityRuntime`'s existing engine-injection constructor already provides this seam, satisfying "do not create new runtime components."

## Future Impact

This ADR becomes the canonical reference for any future MWO implementing Steps 1–6 of the Migration Strategy. Any such MWO must cite which step it implements, must not skip BRAIN's Outcome-stage gap before Step 2, must not treat Section 1 (current state) as if it were already Section 2 (target state), and must preserve BRAIN, Knowledge, and Capability as AI5R-level peer assets rather than relocating or scoping them into OSA. A future product (Education OS, Manufacturing OS, or any other) consuming BRAIN, Knowledge, or Capability independently of OSA is explicitly anticipated and permitted by this ADR, not a deviation from it.

## Supersedes

None.
