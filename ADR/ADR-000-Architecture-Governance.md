# ADR-000 — Architecture Governance

## Status

Proposed

## Context

The repository now contains four distinct kinds of architectural documentation — the Blueprint (`BLUEPRINT/`, frozen per `BLUEPRINT/FREEZE.md`), ADRs (`ADR/ADR-001` through `ADR-003`), the Engineering Standard (`ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`), and Manufacturing Work Orders (`ENGINEERING/MWO/*.md`) — each produced independently across this session and prior sprints, without a single document stating what each kind is for, who may change it, and how they relate to one another. ADR-001 through ADR-003 each individually cited the Blueprint and, in ADR-002/003, referenced Engineering Standard-adjacent concepts, but no document has yet defined the governance model itself. This ADR does that, and only that — it introduces no new architecture and revises no existing decision.

---

## Decision

### 1. Blueprint

**Purpose.** States what AI5R and OSA are: vision, philosophy, product positioning, and formal enterprise architecture (`BLUEPRINT/OSA/v1.0/Volume-01-Executive-Blueprint.md`, `Volume-02-Enterprise-Architecture.md`).

**Authority.** Highest in the repository. Per `BLUEPRINT/README.md`'s Governance section, the Blueprint is owned at the Chief Architect level; no other document type may override it.

**Scope.** Vision, philosophy, product definition, layered structure, Enterprise Object model, Capability architecture, AI Workforce hierarchy, and the rules governing how OSA Systems and Instances are composed. Applies across every AI5R product, not only OSA.

**Allowed Content.** Statements of what is true of the architecture — definitions, principles, structural diagrams, and the rules in `BLUEPRINT/OSA/v1.0/Volume-02-Enterprise-Architecture.md` Chapter 10 ("Architecture Rules").

**Forbidden Content.** Implementation detail, code, file paths as normative requirements, sprint planning, or any content whose correctness depends on a specific repository state at a point in time (that belongs to an MWO or an audit report, not the Blueprint).

**Versioning.** Per `BLUEPRINT/README.md`: versioned as a whole (`v1.0`, `v2.0`, …), not per volume. Corrections that don't change meaning are recorded in `CHANGELOG.md` without incrementing the version. A new major version is issued only when vision, architecture, or philosophy materially changes.

**Approval Process.** A volume is drafted, reviewed against everything already frozen, and does not become official until persisted under `OSA/vX.Y/` and reviewed (`BLUEPRINT/README.md`, Review Process). Freezing is a separate, explicit act from persisting (per `FREEZE.md`).

**Modification Rules.** Per `FREEZE.md`'s Conditions Required to Unfreeze: an explicit named trigger, a recorded decision (an ADR, not an inline edit), Chief Architect approval, and — if Volume I or II is touched — a consistency re-check against every other frozen element. No frozen Blueprint element may be silently changed.

**Freeze Rules.** Volume I, Volume II, ADR-001's recorded Decision Topics, and `DECISIONS.md` are frozen as of MWO-BP-008 (`FREEZE.md`). This is a foundation freeze, not a full v1.0 release freeze — Volumes III–VI remain open and are written *against* the frozen foundation, each frozen individually as completed.

---

### 2. ADR (Architecture Decision Record)

**Purpose.** Records a specific architectural decision — a relationship, an ownership boundary, a role definition — made in service of, and consistent with, the Blueprint, at a level of resolution the Blueprint itself does not state.

**Authority.** Second to the Blueprint. An ADR may elaborate the Blueprint at engineering resolution (as ADR-002 does for BRAIN, ADR-003 does for Capability) but may never contradict it. An ADR outranks an Engineering Standard or an MWO on any question of architectural decision.

**Scope.** One decision, or one closely related family of decisions, per ADR — ownership relationships, dependency direction, role definitions between named architectural components. Not a catalogue of all decisions ever made (that is what `ADR_INDEX.md` is for) and not an implementation plan.

**Allowed Content.** Status, Context, Decision, Consequences, Alternatives Considered, Future Impact, Supersedes — the structure established by ADR-001 through ADR-003. Diagrams and rules that state a decision, not a build sequence.

**Forbidden Content.** Vision or philosophy restatement that belongs in the Blueprint; step-by-step implementation instructions that belong in an MWO; process/reporting conventions that belong in the Engineering Standard; and — critically — any content that revises a frozen Blueprint element without following `FREEZE.md`'s unfreeze conditions.

**Relationship with Blueprint.** An ADR must cite the specific Blueprint chapter or principle it elaborates (as ADR-002 cites Vol. II Ch.3/7 and ADR-003 cites Vol. II Ch.6). It never overrides the Blueprint; where an ADR appears to conflict with a frozen Blueprint element, the Blueprint prevails until the ADR is revised or the Blueprint is formally unfrozen.

**Relationship with MWO.** An ADR states what is architecturally true; an MWO states what implementation work is authorized to make the repository conform to that truth. An MWO may reference an ADR as its authority; an ADR never references an MWO as its authority, since ADRs are decided independent of any specific implementation attempt.

**Relationship with Source Code.** An ADR describes target and/or current-state architecture; it does not itself change source code. Where an ADR's Section separates "Current Repository Architecture" from "Target AI5R Architecture" (as ADR-002 does), source code is only ever evidence for the former, never authority for the latter.

**Approval Process.** Drafted (typically as an MWO's deliverable), reviewed by the Chief Architect, revised in place across rounds (as ADR-002 was revised twice before approval), and persisted to `ADR/` with `ADR_INDEX.md` updated — matching the Engineering Standard's Document Drafting Mode (§13). Commit and push each require their own separate, explicit approval, per the Engineering Standard's Commit and Push Standards (§10–11).

---

### 3. Engineering Standard

**Purpose.** Per `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` §1: defines how implementation work is planned, reviewed, executed, validated, and reported — a process standard, not an architecture document.

**Authority.** Governs engineering *process* with the same mandatory force the Blueprint has over architecture and ADRs have over decisions, but strictly within its own scope: it has no authority to state what the architecture is or should be.

**Scope.** Sprint lifecycle, MWO lifecycle, Work Package lifecycle, canonicalization standard, evidence standard, validation standard, review/commit/push standards, engineering vocabulary, and Definition of Done — all process, all product-agnostic (per its own §0 Scope Note).

**Relationship with ADR.** The Engineering Standard never makes an architectural decision; it states how any decision — including one recorded in an ADR — is to be drafted, reviewed, approved, and reported. Where an MWO produces an ADR as its deliverable (as this session's MWOs did), the Engineering Standard's Document Drafting Mode (§13) governs *how* that ADR is produced; the ADR itself, once approved, is what governs the decision's content.

**Relationship with Blueprint.** The Engineering Standard operates entirely beneath the Blueprint's authority and never restates or revises it. It codifies practice (per its own §0: "this document standardizes, it does not invent"), consistent with whatever the Blueprint and applicable ADRs already establish.

**Relationship with Source Code.** The Engineering Standard governs the *process* by which source code may be touched — specifically, per its Execution Modes (§13), only Implementation Mode, governed by an approved MWO's Work Package Lifecycle, may create or modify product code. Analysis Mode and Document Drafting Mode, the modes this entire ADR chain has operated in, never touch source code.

---

### 4. Manufacturing Work Order (MWO)

**Purpose.** The unit of approved implementation or investigation scope — per the Engineering Standard's Engineering Vocabulary (§15), "the unit of approved implementation scope."

**Authority.** Lowest of the four document types in architectural precedence, but the only one with direct authority to authorize touching source code (via its Work Package Lifecycle, in Implementation Mode). An MWO has no authority to decide architecture — it may only implement, investigate, or draft a document (such as an ADR) reflecting a decision the Chief Architect makes in reviewing it.

**Scope.** Exactly what its own document states — per the Engineering Standard's Execution Modes (§13) and the standing Execution Protocol (`CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md`): "The active Manufacturing Work Order defines your entire universe. Everything outside the current MWO is out of scope."

**Relationship with ADR.** An MWO may produce an ADR as its deliverable (as MWO-ADR-001 through this ADR-000 have), or may implement work an already-approved ADR authorizes (per ADR-002/003's Migration Strategy and Future Impact sections). An MWO may never itself constitute an architectural decision — the decision is the Chief Architect's, recorded in the ADR the MWO produces or cites.

**Relationship with Blueprint.** An MWO operates within whatever the Blueprint and applicable ADRs already establish. Per the standing Execution Protocol: "Architecture is frozen. Never redesign architecture... If architecture ambiguity appears: STOP. Explain. Wait." An MWO that encounters a genuine architectural gap does not resolve it — it reports the gap and a new ADR (or Blueprint volume, if foundational) is the correct next step.

**Relationship with Engineering Standard.** Every MWO is executed under the Engineering Standard's process rules — its lifecycle, its approval granularity requirement, its validation categories, its commit/push separation. An MWO document may state specifics (e.g., which work packages batch together) but may not contradict a Mandatory rule in the Engineering Standard.

**Completion Criteria.** Per the Engineering Standard §14 (Definition of Done, for an MWO): every work package in its approved scope is individually complete, no file outside its approved scope was touched (verified, not assumed), any locked canonical mapping remained unchanged throughout, a completion report exists aggregating all work package results, and nothing is committed or pushed without separate, explicit approval for each.

**Verification Criteria.** Per the Engineering Standard §8 (Validation Standard): Structural Validation (syntax, canonical targeting, scope check) is always in scope; Runtime Verification (live execution, live data-store, integration) is a distinct category, never implied by a Structural Validation PASS, and if not performed, that must be stated explicitly along with the specific reason.

---

### 5. Source Code

Source code implements whatever the Blueprint, the applicable ADRs, and the applicable Engineering Standard rules already establish, as authorized by an approved MWO. It is never itself a source of architectural authority — a pattern found in source code is evidence of current state (as this session's MWO-OSA series repeatedly established), never evidence of what the architecture *should* be. Where source code and a governing document disagree, the document governs and the code is the thing due to change, not the reverse — this is the same principle the standing Execution Protocol states as "Implementation follows architecture. Architecture never follows implementation."

**Conformance direction, stated explicitly and required to hold in this order only:**

```
Blueprint
    ↓
ADR
    ↓
Engineering Standard
    ↓
MWO
```

Source code conforms to all four, in the order above. Never the reverse — no document type above may be revised merely because source code currently does something different; that discrepancy is a finding to report, not a justification to alter the document.

---

### 6. Hierarchy

The canonical governance hierarchy, end to end:

```
AI5R Vision
    ↓
Blueprint
    ↓
ADR
    ↓
Engineering Standard
    ↓
MWO
    ↓
Implementation
    ↓
Verification
    ↓
Release
```

Each stage is authorized by, and answerable to, the stage above it. No stage may reach upward and redefine the one above it — an MWO cannot redefine an Engineering Standard rule, an Engineering Standard cannot redefine an ADR's decision, an ADR cannot redefine a frozen Blueprint element without following `FREEZE.md`'s unfreeze process, and nothing redefines AI5R Vision, which is the premise every other layer serves.

---

### 7. Architecture Rules

- **Blueprint defines architecture.** It is the sole source of vision, philosophy, and formal enterprise-architecture truth.
- **ADR defines decisions.** It resolves a specific architectural question at engineering resolution, consistent with the Blueprint, and becomes the reference for implementation that follows.
- **Engineering Standard defines engineering rules.** It governs process — how work is planned, reviewed, executed, validated, reported, committed, and pushed — never what the architecture is.
- **MWO defines implementation work.** It is the unit of approved scope authorized to touch source code, draft a document, or perform an investigation, strictly within what it states.
- **Source code implements the approved architecture.** It is evidence of current state, never authority over target state.
- **No document may redefine the responsibility of another document.** An ADR may not restate Blueprint vision; an Engineering Standard may not make an architectural decision; an MWO may not author a rule that binds future MWOs the way an Engineering Standard does; source code may not be treated as if it were any of the above.

---

## Consequences

### Positive
- Gives every future MWO in this repository a single reference for which document type governs which question, ending the ambiguity that led to this ADR being requested in the first place.
- Makes explicit, for the first time, that an MWO may produce an ADR as its deliverable without itself constituting architectural authority — resolving a distinction this session's MWO-ADR-001 chain relied on implicitly but never stated.
- Establishes a strict, one-directional conformance order (Blueprint → ADR → Engineering Standard → MWO → Source Code) that prevents future work from justifying a document change by pointing to what source code currently does.

### Negative
- This ADR is itself governed by the rules it states — any future revision to it must follow the same ADR approval process (Section 2) it defines, including explicit Chief Architect review and, if it touches a frozen Blueprint element, the unfreeze conditions in `FREEZE.md`.
- Retroactively, this ADR does not audit whether ADR-001 through ADR-003 or the existing MWO archive already violate the boundaries stated here — that would be a new discovery sprint, out of scope for this governance-definition MWO.

## Alternatives Considered

- **Fold governance rules into the Engineering Standard instead of a new ADR.** Rejected — the Engineering Standard governs process, not the relationship between architecture-defining document types; conflating the two would blur exactly the boundary this ADR exists to draw.
- **Leave governance implicit, as it has been through ADR-001–003.** Rejected per Chief Architect direction: continued architecture expansion without an explicit governance model risks exactly the kind of undocumented drift this whole MWO-OSA/ADR series was launched to eliminate.
- **Number this document ADR-004, continuing the existing sequence.** Rejected in favor of `ADR-000`, per the Chief's explicit instruction — its role as the foundation every other ADR is read against is better served by a number that precedes the sequence it governs, rather than extending it.

## Future Impact

This ADR becomes the canonical reference for every future ADR, Engineering Standard revision, and MWO produced in this repository. Any future document that blurs the boundaries stated in Section 7 (e.g., an MWO attempting to record an architectural decision without a corresponding ADR, or an ADR restating Blueprint vision rather than citing it) is in violation of this ADR and should be revised before proceeding. No further architecture expansion is approved until this governance model is itself approved, per the Chief Architect's direction opening this sprint.

## Supersedes

None. This ADR does not revise ADR-001, ADR-002, or ADR-003 — it defines the governance model those and all future ADRs operate under.
