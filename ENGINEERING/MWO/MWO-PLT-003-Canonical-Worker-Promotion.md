# MWO-PLT-003 — Canonical Worker Promotion

Status: **WP-001–WP-006 APPROVED. Planning phase CLOSED. Worker workstream now FROZEN by explicit Chief Architect directive.** WP-006 disposition: APPROVED ("Planning PASS. Architecture PASS. Migration Strategy PASS. The Worker Promotion architecture is now sufficiently specified."). **This workstream has transitioned from Planning to Manufacturing — and Manufacturing-phase work (WP-007 Deprecation Strategy, WP-008 Implementation Plan) is SUSPENDED, effective immediately, per separate Chief Architect directive:** engineering priority shifts to LTSA Manufacturing (Pump → Seal → Installation → Maintenance → Integration → Demo, target: LTSA v1.0 running by Monday). WP-007/WP-008 resume only if LTSA Manufacturing work surfaces a direct blocker requiring the Worker Compatibility Layer, or on a separate future Chief Architect directive — whichever comes first. No further platform research is authorized unless a blocking architectural issue is discovered. One open item carries forward, not resolved by this freeze: Capability Descriptor's concrete shape (named and scoped by WP-005 Gap 3, not yet specified) must be defined before `ManufacturingWorkerAdapter` can be implemented, if/when WP-007/WP-008 resume. No implementation, no migration, no runtime modification, no adapter implementation, no Worker modification, no code has been performed anywhere in WP-001–WP-006, and none will be performed while frozen.
Type: Platform Work Order — implementation of `ADR-AR-003` / `ARCH-REVIEW-003` Option A' (Canonical Promotion Strategy)
Epic: AI5R Platform — Canonical Worker Promotion, Phase 1–2 of 4 complete at decision/planning level ("Promote" complete; "Maintain Compatibility" specified, validated, Decided); Phase 3–4 (Gradual Migration/Retirement) SUSPENDED per `ARCH-REVIEW-003` §5 and Chief Architect freeze directive
Role: Implementation Engineer
Architecture: Platform Foundation LOCKED. `ARCH-REVIEW-003` FROZEN. This MWO implements the already-decided canonical target and compatibility strategy; it does not redesign, re-select, or re-open either decision. It also does not decide the five open gaps itself — recommendations are offered, decisions are reserved for the Chief Architect, consistent with the Constitution's Canonical Rule.
Basis: Direct re-read of `AI5R-SDK/RUNTIME/{enterprise_worker,task_execution_engine,worker_assignment_engine,mission_runtime,enterprise_task}.py`; `AI5R-SDK/WORKFORCE/worker.py`; `AI5R-SDK/ORGANIZATION/organization_worker.py`; `AI5R-SDK/MANUFACTURING_CENTER/manufacturing_worker.py`; `AI5R-SDK/DIGITAL_EMPLOYEE/{digital_employee,employee_capability}.py`; `ENGINEERING/MWO/ARCH-REVIEW-003-Canonical-Worker-Review.md` §1–§6; this MWO's own WP-002, WP-003, and WP-004.
Scope: WP-001–WP-006 (complete, approved, all five gaps Decided, Migration Plan produced and closed). No file under `AI5R-SDK`, `PRODUCTS`, or anywhere else was created or modified — no runtime modification, no lifecycle modification, no Worker modification, no migration, no implementation, no adapter implementation, no code. WP-007/WP-008 are explicitly out of scope while the freeze holds.

**Work Package Roadmap (current numbering):**

| WP | Title | Status |
|---|---|---|
| WP-001 | Canonical Worker Identification | APPROVED |
| WP-002 | Compatibility Layer Design | APPROVED |
| WP-003 | Compatibility Specification | APPROVED |
| WP-004 | Compatibility Validation | APPROVED |
| WP-005 | Gap Resolution Decision | **APPROVED** — all five gaps Decided by Chief Architect; Compatibility Principle added |
| WP-006 | Migration Plan | **APPROVED.** Planning phase closed — workstream now in Manufacturing |
| WP-007 | Deprecation Strategy | **SUSPENDED** — Worker workstream frozen; resumes only on a direct LTSA Manufacturing blocker or a separate Chief Architect directive |
| WP-008 | Implementation Plan | **SUSPENDED** — same freeze as WP-007 |

---

## WP-001 — Canonical Worker Identification

### 1. Selected Canonical Worker (Confirmed)

Per `ARCH-REVIEW-003` §3 (Option A) and §5 (Option A' — same canonical target as Option A; only the migration sequencing differs), the Canonical Worker for **UWP-001** is:

| | |
|---|---|
| **Canonical Type** | `EnterpriseWorker` |
| **Canonical Contract** | `Worker(Protocol)` |
| **Location** | `AI5R-SDK/RUNTIME/enterprise_worker.py:10` (`EnterpriseWorker`), `AI5R-SDK/RUNTIME/task_execution_engine.py:6-8` (`Worker(Protocol)`) |
| **Existing orchestration already built around it** | `WorkerAssignmentEngine` (`worker_assignment_engine.py`), `TaskExecutionEngine` (`task_execution_engine.py`), `MissionRuntime` (`mission_runtime.py`) |

No file is created or modified to record this confirmation — this is an identification and rationale record only, per WP-001's explicit "no code changes" scope.

### 2. Rationale (re-verified by direct read, not re-cited from prior documents)

Re-reading the four `RUNTIME/` files directly (not relying solely on `ARCH-REVIEW-003`'s own citations) confirms, as of this WP:

1. **`EnterpriseWorker` is the only one of the five Worker concepts with a real `execute()` hook and a structural `Protocol` already defined around it** (`Worker(Protocol)`, `task_execution_engine.py:6-8`), satisfied by `EnterpriseWorker` today.
2. **A working three-part orchestration chain already exists and is exercised by tests**: `MissionRuntime.run()` → dequeues a task → `WorkerAssignmentEngine.assign()` (matches by `worker.supports(task.task_type)`) → `TaskExecutionEngine.execute()` (drives `task.start()` → `worker.execute(task)` → `task.complete()`/`task.fail()`). Confirmed by direct read of `mission_runtime.py:24-48`; no other Worker concept (`WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE`) has an equivalent full chain already wired and tested.
3. **This matches the precedent already applied to UMR-001** (`MWO-LTSA-049`): promote the existing implementation already built around the right domain concepts, rather than build a new one — the same reasoning `ADR-AR-003` now formalizes as platform-wide default.

### 3. Known Gaps in the Canonical Worker (carried forward, not fixed by WP-001)

Re-confirmed by direct read for this WP, precisely:

- **`EnterpriseWorker.execute()` unconditionally raises `NotImplementedError`** (`enterprise_worker.py:27-30`) — there is no safe base-class default; every consumer must override it.
- **`EnterpriseWorker.status` is never transitioned by any existing code path.** Direct read of `worker_assignment_engine.py` and `mission_runtime.py` confirms neither `WorkerAssignmentEngine.assign()` nor `MissionRuntime.run()` ever reads or writes `worker.status` — it remains at its `"idle"` default for the lifetime of the object, regardless of assignment or execution outcome. This is a **more precise finding than `ARCH-REVIEW-003` §2's "unclear/unconfirmed"** — now confirmed absent, not merely unclear.

These gaps are **not fixed here.** WP-001's scope is identification and rationale only. Whether/how to close them is a decision for WP-002 (Compatibility Layer Design) or later, at the Chief Architect's direction — not decided unilaterally in this WP.

### 4. Consumers Confirmed Unaffected

`WorkerAssignmentEngine`, `TaskExecutionEngine`, `MissionRuntime`, and their respective test suites (`test_worker_assignment_engine.py`, `test_task_execution_engine.py`, `test_mission_runtime.py`, `test_enterprise_worker.py`) are unmodified — this WP performed zero writes to any of them. The other four Worker concepts (`WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE`) and their consumers are likewise untouched.

---

## Deliverables (WP-001 only)

- This document. No file under `AI5R-SDK`, `PRODUCTS`, or elsewhere was created or modified.

## Definition of Done — WP-001

- Canonical Worker confirmed: `EnterpriseWorker` / `Worker(Protocol)` (`AI5R-SDK/RUNTIME/`).
- Rationale re-verified by direct code read, not re-cited assumption.
- Known gaps (execute() raises, status never transitions) re-confirmed precisely, disclosed, not fixed.
- No code changes performed anywhere.
- Nothing committed or pushed.

**WP-001 disposition (per Chief Architect review):** APPROVED. The `EnterpriseWorker.status` finding is accepted as a separate runtime issue — **not addressed in WP-002 or any part of this MWO** unless separately, explicitly authorized.

---

## WP-002 — Compatibility Layer Design

**Strict scope, as instructed:** design of the compatibility interfaces only. No runtime modification. No lifecycle modification. No state transition changes. No implementation. Nothing in this section writes, wraps, or executes any code — every class/method shown below is a **design specification**, not a file written to the repository.

### 1. What "Compatibility Layer" Means at This Stage

Per `ARCH-REVIEW-003` §5 Phase 2 ("Maintain Compatibility"): the four non-canonical Worker concepts (`WORKFORCE.Worker`, `ORGANIZATION.OrganizationWorker`, `MANUFACTURING_CENTER.ManufacturingWorker`, `DIGITAL_EMPLOYEE.DigitalEmployee`) must be able to continue operating **completely unchanged**, while becoming addressable through the canonical Worker's orchestration chain (`WorkerAssignmentEngine` → `TaskExecutionEngine` → `MissionRuntime`) via a wrapping adapter — not by modifying any of the four classes themselves, and not by modifying `RUNTIME/*.py`.

### 2. The Real Compatibility Surface (wider than the named Protocol alone)

Direct re-read of the three orchestration files shows the practical surface a registrable Worker must expose is **not just** `Worker(Protocol)`'s single `execute()` method — `WorkerAssignmentEngine`/`MissionRuntime` also read two more members:

| Member | Read By | Purpose |
|---|---|---|
| `.worker_id: str` | `WorkerAssignmentEngine.assign()` → `task.assign(worker.worker_id)` (`worker_assignment_engine.py:18`) | Identifies which worker a task was assigned to |
| `.supports(task_type: str) -> bool` | `WorkerAssignmentEngine.assign()` (`worker_assignment_engine.py:17`) | Match-by-capability gate |
| `.execute(task: EnterpriseTask) -> Dict[str, Any]` | `TaskExecutionEngine.execute()` (`task_execution_engine.py:16`), the named `Worker(Protocol)` method | Performs the work |

**Design specification — `WorkerCompatibilityAdapter` (interface only, no file written):**
```
class WorkerCompatibilityAdapter(Protocol):
    worker_id: str
    def supports(self, task_type: str) -> bool: ...
    def execute(self, task: EnterpriseTask) -> Dict[str, Any]: ...
```
Every concrete adapter below is a design that would wrap **one instance** of its legacy type and satisfy this shape — the legacy type's own class definition is never modified.

### 3. Per-Legacy-Type Adapter Design

#### 3.1 `WorkforceWorkerAdapter` (wraps `WORKFORCE.Worker`)

| Member | Design | Confidence |
|---|---|---|
| `.worker_id` | Direct passthrough: `wrapped.worker_id` | Clean |
| `.supports(task_type)` | **Open question, not resolved here.** `Worker.can_handle(required_role, required_skills)` matches on a `role` string and a `skills` list — there is no single `task_type` string in its own model. Two candidate mappings exist (treat `task_type` as a role match, or as single-skill membership) and neither reads as more correct than the other from `Worker`'s own semantics. | **Flagged (§4)** |
| `.execute(task)` | **Genuine gap.** `Worker` has no execution method of any kind — only `assign()`/`release()`/`can_handle()`/`add_experience()`, all bookkeeping, confirmed by direct read (`worker.py:16-47`). Design position: adapter's `execute()` raises `NotImplementedError`, identical in spirit to `EnterpriseWorker`'s own base behavior — not a new failure mode, but a disclosed confirmation that this legacy Worker contributes no executable behavior today. | Confirmed gap, not resolved |

#### 3.2 `OrganizationWorkerAdapter` (wraps `ORGANIZATION.OrganizationWorker`)

| Member | Design | Confidence |
|---|---|---|
| `.worker_id` | Direct passthrough: `wrapped.worker_id` | Clean |
| `.supports(task_type)` | `task_type in wrapped.capabilities` — `capabilities: Dict[str, Any]` is already keyed exactly the way `OrganizationWorkerRegistry.find_by_capability()` uses it today (`capability_key in worker.capabilities`, confirmed by direct read). | **Clean — the one unambiguous adapter of the four** |
| `.execute(task)` | **Genuine gap**, same as 3.1: `OrganizationWorker` has only `to_dict()`, confirmed no execution method exists (`organization_worker.py:8-22`). Design position: `NotImplementedError`, same rationale. | Confirmed gap, not resolved |

#### 3.3 `ManufacturingWorkerAdapter` (wraps `MANUFACTURING_CENTER.ManufacturingWorker`)

| Member | Design | Confidence |
|---|---|---|
| `.worker_id` | **Genuine gap.** `ManufacturingWorker` is stateless with no `__init__` override and no identity field of any kind (confirmed, `manufacturing_worker.py:18-23`). The adapter would need to synthesize an id at adapter-construction time — a design decision, not a mechanical translation. | **Flagged (§4)** |
| `.supports(task_type)` | **Genuine gap.** `ManufacturingWorker` has no capability/type concept — it executes any well-formed node unconditionally. Nothing in the wrapped object answers a capability question. | **Flagged (§4)** |
| `.execute(task: EnterpriseTask)` | `ManufacturingWorker.execute(node)` requires `node.node_id` (a non-empty string, confirmed `manufacturing_worker.py:42-45`). `EnterpriseTask` has `task_id`, not `node_id` (confirmed, `enterprise_task.py:16`) — a field-mapping decision (`task.task_id → node_id`), not a mechanical one. The return shape (`{"node_id","node","status","metadata"}`) already satisfies `Dict[str, Any]` with no translation needed. | **Flagged (§4)** for the input mapping only |

#### 3.4 `DigitalEmployeeAdapter` (wraps `DIGITAL_EMPLOYEE.DigitalEmployee`)

| Member | Design | Confidence |
|---|---|---|
| `.worker_id` | Direct passthrough: `wrapped.employee_id` (confirmed field, `digital_employee.py:25/33`) | Clean |
| `.supports(task_type)` | `task_type in wrapped.capabilities` — confirmed `capabilities: list[str]` (`digital_employee.py:12,17`), same clean shape as 3.2 | Clean |
| `.execute(task: EnterpriseTask)` | **Genuine signature gap.** `DigitalEmployee.execute()` takes **no task parameter** — it reads `self.current_task` (a plain string), set by a prior `self.assign(task: str)` call (confirmed, `digital_employee.py:64-74`), and returns `{"employee","task","status":"EXECUTED"}`, not an `EnterpriseTask`-shaped result. To satisfy `Worker(Protocol)`, the adapter would need to call `wrapped.assign(task.task_id)` immediately before `wrapped.execute()` — this triggers `DigitalEmployee`'s own pre-existing `status="WORKING"` transition (already defined by the wrapped class, not new logic invented by the adapter), but it is a two-call sequence worth surfacing explicitly rather than building in silently. | **Flagged (§4)** for the two-call sequencing |

### 4. Design Decisions Requiring Chief Architect Confirmation Before WP-003

Per the Constitution's Canonical Rule ("If canonical ambiguity appears: STOP. Report. Wait. Do not decide"), the following are surfaced, not resolved, by this design:

1. **`WorkforceWorkerAdapter.supports()` mapping** — role-match vs. skill-membership, both plausible, neither decided.
2. **`ManufacturingWorkerAdapter.worker_id` synthesis** — the wrapped type has no identity of its own; how one is generated is a decision, not a translation.
3. **`ManufacturingWorkerAdapter.supports()`** — the wrapped type has no capability concept to translate from at all; whether it should always return `True`, always `False` pending a real filter, or require an out-of-band capability declaration is undecided.
4. **`ManufacturingWorkerAdapter.execute()` field mapping** — whether `EnterpriseTask.task_id` is the correct source for the required `node_id`, or whether a different field/convention should be used.
5. **`DigitalEmployeeAdapter.execute()` two-call sequencing** (`assign()` then `execute()`) — confirmed necessary, not confirmed as the *only* acceptable design; an alternative would refuse to adapt `DigitalEmployee` until its own `execute()` signature changes, which would touch `DIGITAL_EMPLOYEE` code and is explicitly out of scope for a compatibility-layer (non-invasive) design.

No adapter for `WorkforceWorkerAdapter` or `OrganizationWorkerAdapter`'s `execute()` gap is proposed to be "fixed" here — both legacy types genuinely have no execution logic today, and inventing any would be new implementation logic, out of this WP's scope.

### 5. Explicitly Out of Scope for WP-002 (carried forward, not touched)

- **`EnterpriseWorker.status` never transitioning** (WP-001 finding) — accepted as a separate runtime issue per Chief Architect direction; not addressed by any adapter design above.
- **No adapter modifies its wrapped class.** Every adapter is a pure wrapper; zero lines of `WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, or `DIGITAL_EMPLOYEE` code are touched.
- **No adapter is registered into `WorkerAssignmentEngine`** by this WP — that is a WP-004/Migration Plan concern, not a design-only WP-002 concern.
- **Suggested future location** (not created): `AI5R-SDK/RUNTIME/COMPATIBILITY/`, mirroring `RUNTIME/`'s existing flat-file convention — a placement suggestion only, to be confirmed, not acted on, before any file is written.

---

## Definition of Done — WP-002

- Compatibility interface (`WorkerCompatibilityAdapter`) and four per-type adapter designs specified.
- Every design grounded in direct re-read of both the canonical Worker's orchestration chain and each legacy type's actual code — no assumption stated as fact.
- Five genuine open design questions (§4) surfaced for Chief Architect confirmation, none decided unilaterally.
- No runtime modification, no lifecycle modification, no state transition changes, no implementation.
- Nothing committed or pushed.

**WP-002 disposition:** APPROVED ("Excellent scope discipline"). Roadmap adjustment follows below — WP-003 is now Compatibility Specification, inserted before Migration Plan.

---

## WP-003 — Compatibility Specification

**Strict scope, as instructed:** formalize the Compatibility Layer designed in WP-002 into a specification covering interface contract, lifecycle, capability mapping, identity mapping, error behavior, adapter responsibilities, unsupported behavior, and execution semantics. **Resolve none of WP-002 §4's five open gaps — document them, in their proper category, only.** No code, no runtime changes, no Worker changes, no migration, no implementation.

### 1. Interface Contract

The compatibility surface is exactly the three members identified in WP-002 §2 — no more, no less:

| Member | Type | Contract |
|---|---|---|
| `worker_id` | `str` | Must be non-empty and stable for the entire lifetime of the adapter instance (never regenerated between calls). |
| `supports(task_type: str)` | `(str) -> bool` | Must return a `bool`. Must not raise. Must not have side effects (no mutation of the wrapped object). |
| `execute(task: EnterpriseTask)` | `(EnterpriseTask) -> Dict[str, Any]` | Must return `Dict[str, Any]` on success. May raise — see §5 Error Behavior. Is permitted to delegate to the wrapped object's own methods and thereby trigger the wrapped object's own pre-existing state transitions (not new ones). |

Every adapter (`WorkforceWorkerAdapter`, `OrganizationWorkerAdapter`, `ManufacturingWorkerAdapter`, `DigitalEmployeeAdapter`) must satisfy this contract exactly as specified in WP-002 §3. This section formalizes the shape already designed; it does not change it.

### 2. Lifecycle

The adapter has **no lifecycle of its own** — this is a deliberate, load-bearing property, not an oversight:

- An adapter wraps exactly one instance of its legacy type at construction time and holds that single reference for its entire lifetime.
- The adapter introduces **zero new states**. Whatever lifecycle the wrapped object already has (`Worker`'s `AVAILABLE`/`BUSY`, `OrganizationWorker`'s static `ACTIVE`, `ManufacturingWorker`'s stateless design, `DigitalEmployee`'s multi-state machine) continues entirely unchanged, driven only by the wrapped object's own pre-existing methods.
- The adapter's own "lifecycle" is therefore just: **constructed → used any number of times → discarded.** There is no adapter-level `AVAILABLE`/`BUSY`/`ACTIVE` concept, and none is introduced by this specification.

### 3. Capability Mapping — Taxonomy (categories only; per-adapter choice remains open per WP-002 §4)

Every adapter's `supports()` falls into exactly one of three categories. This section names and defines the categories; it does **not** assign a resolution to the two adapters whose category has more than one candidate mapping:

| Category | Definition | Applies To |
|---|---|---|
| **Direct Mapping** | The wrapped object's own data already answers `supports(task_type)` unambiguously, using a mechanism the wrapped type's own code already exercises elsewhere. | `OrganizationWorkerAdapter` (`task_type in capabilities`, matches `find_by_capability()`'s own existing usage), `DigitalEmployeeAdapter` (`task_type in capabilities`) |
| **Ambiguous Mapping** | More than one plausible translation exists from the wrapped object's own model, and the wrapped type's own code does not privilege one over the other. | `WorkforceWorkerAdapter` (role-match vs. skill-membership — **still unresolved, per WP-002 §4 item 1**) |
| **Absent Mapping** | The wrapped object's own model contains no capability or type concept to translate from at all. | `ManufacturingWorkerAdapter` (**still unresolved, per WP-002 §4 item 3**) |

### 4. Identity Mapping — Taxonomy (categories only; synthesis method remains open per WP-002 §4)

| Category | Definition | Applies To |
|---|---|---|
| **Native Identity** | The wrapped object already exposes a stable identifier of its own; the adapter passes it through unchanged. | `WorkforceWorkerAdapter` (`worker_id`), `OrganizationWorkerAdapter` (`worker_id`), `DigitalEmployeeAdapter` (`employee_id`) |
| **Synthesized Identity** | The wrapped object exposes no identifier of its own; the adapter must generate one and hold it stable for the adapter's lifetime (per §2's "no lifecycle of its own" — the synthesized id does not change between calls). | `ManufacturingWorkerAdapter` (**generation method still unresolved, per WP-002 §4 item 2**) |

### 5. Error Behavior

Two distinct error situations exist, and this specification requires they be **distinguishable from each other** — a caller (or future maintainer) must never confuse "the wrapped type has no logic here" with "something actually went wrong":

1. **Unsupported Execution** (see §6): raised when the wrapped legacy type has no execution logic to delegate to at all (`WorkforceWorkerAdapter`, `OrganizationWorkerAdapter`). This is a confirmed, permanent, documented condition of the wrapped type — not a transient failure. It must propagate as an exception (consistent with `EnterpriseWorker`'s own existing base behavior of raising `NotImplementedError`), which `TaskExecutionEngine.execute()` already catches and converts into `task.fail(str(exc))` (confirmed, `task_execution_engine.py:20-22`) — no new error-handling path is introduced; the existing one is reused as-is.
2. **Genuine Execution Failure**: any exception raised by the wrapped object's own delegated call once execution is actually attempted (e.g. a `ManufacturingWorkerAdapter` delegating to `ManufacturingWorker.execute()`, which itself raises `ValueError` for a malformed node, confirmed `manufacturing_worker.py:39-45`). The adapter must **not** catch or suppress this — it must propagate unchanged, exactly as `TaskExecutionEngine.execute()` already expects (its own `try`/`except Exception` block, confirmed, is the single place such failures are handled; an adapter that swallowed the exception would break that existing contract).

**No adapter catches an exception it did not itself raise.** This is a specification requirement, not a suggestion — it preserves `TaskExecutionEngine`'s existing, already-tested error-handling behavior unchanged.

### 6. Adapter Responsibilities (must / must not)

**Every adapter must:**
- Wrap exactly one instance of its legacy type.
- Satisfy the Interface Contract (§1) exactly.
- Delegate every call to the wrapped object's own existing methods — never implement new business logic.
- Let any exception from the wrapped object propagate unchanged (§5).

**Every adapter must not:**
- Modify its wrapped class's own definition, in any file, ever.
- Introduce a new state, status value, or transition not already defined by the wrapped object (§2).
- Silently invent capability or identity data that cannot be derived from the wrapped object — an **Absent Mapping** (§3) or a **Synthesized Identity** (§4) must be resolved by explicit Chief Architect decision, not by adapter-author judgment call.
- Catch or suppress an exception it did not raise itself (§5).
- Perform retries, queuing, batching, or any asynchronous behavior — see §8.

### 7. Unsupported Behavior

**Unsupported Execution** is formally defined as: an adapter's `execute()` method is invoked while wrapping a legacy type that has no execution logic of its own (confirmed today for `WorkforceWorkerAdapter` and `OrganizationWorkerAdapter` — both wrapped types expose no execution method whatsoever, per WP-002 §3.1/§3.2). This specification requires:

- The condition must be raised as an exception at `execute()`-call time, not silently return an empty or placeholder result.
- The condition must be documented on the adapter class itself (e.g., in its own description) so a caller can determine, without invoking it, that a given adapter does not support execution — this is a documentation requirement on the future adapter code, not a runtime check to be designed further here.
- Unsupported Execution is **not** an error in the adapter's own design — it accurately reflects that the wrapped legacy type genuinely has no business logic to run, a pre-existing fact about `Worker` and `OrganizationWorker` this specification does not change.

### 8. Execution Semantics

- **One call in, one result out.** `execute(task)` is a single synchronous delegation — no retries, no queuing, no batching, no async/await, no background work of any kind.
- **No side effects beyond the wrapped object's own.** The adapter itself holds no mutable state (per §2); any state change observed after `execute()` returns is a state change the wrapped object's own method already made, not one the adapter introduced.
- **Return shape is always `Dict[str, Any]`.** Where the wrapped object's own method already returns this shape (`ManufacturingWorker.execute()`, `DigitalEmployee.execute()`), it is passed through unchanged. Where it does not, translating it is a WP-004+ concern once execution is actually attempted for a type currently in the **Unsupported Execution** category — not a concern for the two adapters that never reach the wrapped object's own execute call at all.
- **No timeout, no cancellation.** Neither concept exists anywhere in the canonical Worker's existing orchestration chain (`WorkerAssignmentEngine`, `TaskExecutionEngine`, `MissionRuntime` — confirmed by direct read, none implements either), so the Compatibility Layer introduces neither; doing so would be new implementation logic beyond this specification's scope.

### 9. Explicitly Not Resolved by WP-003 (carried forward from WP-002 §4, unchanged)

This specification adds taxonomy and formal behavior categories; it resolves **none** of the five open items:

1. `WorkforceWorkerAdapter.supports()` — still **Ambiguous Mapping** (§3), no choice made between role-match and skill-membership.
2. `ManufacturingWorkerAdapter.worker_id` — still **Synthesized Identity** (§4), generation method not chosen.
3. `ManufacturingWorkerAdapter.supports()` — still **Absent Mapping** (§3), no default chosen.
4. `ManufacturingWorkerAdapter.execute()` field mapping (`task_id → node_id`) — not confirmed as the correct or only mapping.
5. `DigitalEmployeeAdapter.execute()` two-call sequencing — confirmed necessary (§1, §6), not confirmed as the only acceptable design.

`EnterpriseWorker.status` (WP-001 finding) remains a separate runtime issue, untouched by this specification.

---

## Deliverables (WP-001 + WP-002 + WP-003 only)

- This document. No file under `AI5R-SDK`, `PRODUCTS`, or elsewhere was created or modified.

## Definition of Done — WP-003

- Interface contract, lifecycle, capability mapping taxonomy, identity mapping taxonomy, error behavior, adapter responsibilities, unsupported behavior, and execution semantics all formally specified.
- All five WP-002 §4 open gaps re-stated in their proper taxonomy category, none resolved.
- No code, no runtime changes, no Worker changes, no migration, no implementation.
- Nothing committed or pushed.

**WP-003 disposition:** APPROVED ("Excellent work"). Roadmap adjustment follows below — WP-004 is now Compatibility Validation, inserted before Migration Plan.

---

## WP-004 — Compatibility Validation

**Strict scope, as instructed:** validate the WP-003 Compatibility Specification against every existing Worker concept. Produce a Compatibility Matrix, Validation Matrix, Supported Behaviors, Unsupported Behaviors, Risk Assessment, and Gap Validation. **No implementation, no migration, no runtime modification, no adapter implementation, no Worker changes.** The objective is to confirm — or refute — that the Specification can actually be implemented, before any Migration Plan is written.

### 1. Compatibility Matrix

Every Worker concept checked against the Interface Contract (WP-003 §1), including the canonical Worker itself (which needs no adapter, but is included for completeness):

| Concept | `worker_id` | `supports(task_type)` | `execute(task)` | Lifecycle Impact | Capability Mapping (§3) | Identity Mapping (§4) |
|---|---|---|---|---|---|---|
| `EnterpriseWorker` (canonical — no adapter needed) | Native, already conforms | Native, already conforms (`task_type in self.capabilities`, confirmed `enterprise_worker.py:24-25`) | Native, already conforms in shape (raises by default; overridden per subclass) | None — this **is** the canonical type | N/A — is the source of the contract | N/A — is the source of the contract |
| `WorkforceWorkerAdapter` (wraps `Worker`) | Native Identity — passthrough, conforms | **Blocked** — Ambiguous Mapping, no adapter can be written correctly until resolved | Unsupported Execution (confirmed permanent, no wrapped logic exists) | None — adapter introduces no new state | Ambiguous | Native |
| `OrganizationWorkerAdapter` (wraps `OrganizationWorker`) | Native Identity — passthrough, conforms | Direct Mapping — conforms, ready | Unsupported Execution (confirmed permanent, no wrapped logic exists) | None | Direct | Native |
| `ManufacturingWorkerAdapter` (wraps `ManufacturingWorker`) | **Blocked** — Synthesized Identity, generation method not chosen | **Blocked** — Absent Mapping, no default chosen | Conforms in shape, but **blocked** on the `task_id → node_id` field-mapping decision | None | Absent | Synthesized |
| `DigitalEmployeeAdapter` (wraps `DigitalEmployee`) | Native Identity — passthrough, conforms | Direct Mapping — conforms, ready | Conforms in shape, but **blocked** on confirming the two-call (`assign()` then `execute()`) sequence is acceptable | None (delegates to `DigitalEmployee`'s own pre-existing `WORKING` transition) | Direct | Native |

### 2. Validation Matrix — Does the WP-002 Design Actually Satisfy the WP-003 Specification?

Cross-checking each WP-003 requirement against the WP-002 design (not re-deciding anything — confirming internal consistency between the two documents):

| WP-003 Requirement | WP-002 Design Compliance | Verdict |
|---|---|---|
| §1 `worker_id` stable, non-empty | All four adapters designed as pure passthrough or (for Manufacturing) a to-be-decided synthesis held for adapter lifetime — no design shows regeneration between calls | PASS |
| §1 `supports()` returns `bool`, no side effects | All four designs are read-only translations of existing wrapped data (or raise nothing) — none mutates the wrapped object | PASS |
| §2 No new lifecycle/states introduced | Confirmed — no adapter design in WP-002 defines a new status field or transition; all delegate to the wrapped object's own methods only | PASS |
| §5 Unsupported Execution must propagate as an exception, not a placeholder result | WP-002 §3.1/§3.2 both specify `NotImplementedError`, matching `EnterpriseWorker`'s own base behavior exactly | PASS |
| §5 No adapter catches an exception it did not raise | No WP-002 design includes a `try`/`except` around any delegated call | PASS |
| §6 No adapter modifies its wrapped class | Confirmed — every WP-002 design is described purely as a wrapper; zero lines of any of the four legacy files were touched by WP-002 or WP-003 | PASS |
| §6 Absent/Synthesized gaps must be resolved by Chief Architect decision, not adapter-author judgment | WP-002 §4 and WP-003 §9 both explicitly flag rather than resolve all five gaps | PASS |
| §8 One call in, one result out; no retries/queuing/async | No WP-002 design introduces any of these | PASS |

**No inconsistency found between WP-002's design and WP-003's specification.** The specification accurately describes the design; the design does not violate the specification anywhere checked.

### 3. Supported Behaviors (ready for implementation once WP-005+ is approved — no blocking gap)

- `EnterpriseWorker`'s own native conformance to the Interface Contract — already true today, requires no adapter, no change.
- `OrganizationWorkerAdapter.worker_id` and `.supports()` — Native Identity + Direct Mapping, fully resolved.
- `DigitalEmployeeAdapter.worker_id` and `.supports()` — Native Identity + Direct Mapping, fully resolved.
- `WorkforceWorkerAdapter.worker_id` — Native Identity, fully resolved (only its `.supports()` is blocked, not its identity).
- **Unsupported Execution** for `WorkforceWorkerAdapter` and `OrganizationWorkerAdapter` — this is itself a fully specified, implementable behavior (raise `NotImplementedError`, documented on the class), not a blocked one. Its being "unsupported" is a confirmed, permanent, correct fact about the wrapped types, not an open question.
- Lifecycle non-modification (§2) and error-propagation reuse (§5, §6) — apply identically and without any open question to all four adapters.

### 4. Unsupported Behaviors (confirmed permanent — not blocking, not a design defect)

- `WorkforceWorkerAdapter.execute()` and `OrganizationWorkerAdapter.execute()` are confirmed, by direct re-read of both wrapped classes (`worker.py:16-47`, `organization_worker.py:8-22`), to have **no underlying execution logic to delegate to, at all** — this is a fact about the legacy types themselves, not a gap in the Compatibility Layer's design. Per WP-003 §7, this is formally **Unsupported Execution**, a valid and correctly-specified terminal state, not an implementation blocker.

### 5. Risk Assessment

| If Implemented Without Resolving the Gap | Risk | Severity |
|---|---|---|
| `WorkforceWorkerAdapter.supports()` implemented with an unreviewed guess (e.g. silently choosing role-match) | Tasks could be silently mis-routed to a `Worker` whose skills don't actually match, or correctly-matching workers could be silently excluded — a correctness risk affecting task assignment, not a crash | **Medium** — wrong behavior, not a failure; could go unnoticed until a real mis-assignment occurs |
| `ManufacturingWorkerAdapter.worker_id` implemented with an unreviewed synthesis method | If synthesized non-deterministically (e.g. fresh UUID per adapter construction rather than per underlying concept), the same conceptual worker could appear as multiple distinct identities across separate registrations — a correctness risk for any future worker registry or audit trail | **Medium** — silent identity fragmentation, hard to detect after the fact |
| `ManufacturingWorkerAdapter.supports()` implemented with an unreviewed default (e.g. always `True`) | Would let a `ManufacturingWorker` "support" any task type unconditionally, defeating the entire purpose of capability-gated assignment for this adapter | **High** — directly undermines `WorkerAssignmentEngine`'s own matching guarantee for this one adapter |
| `ManufacturingWorkerAdapter.execute()` field mapping implemented with an unreviewed choice (`task_id → node_id`) | If wrong, every delegated call could raise `ValueError` from `ManufacturingWorker.execute()`'s own validation (confirmed, `manufacturing_worker.py:44-45`) — a visible failure, not silent | **Low-Medium** — wrong choice fails loudly and immediately, unlike the two above |
| `DigitalEmployeeAdapter.execute()` two-call sequencing implemented without confirmation | Low risk — the sequence is already confirmed necessary and consistent with `DigitalEmployee`'s own existing `assign()`→`execute()` usage pattern (confirmed, `digital_employee.py:64-74`); the only open question is acceptability of the pattern itself, not its correctness | **Low** |

**Overall: two gaps (`ManufacturingWorkerAdapter.supports()` default, `WorkforceWorkerAdapter.supports()` mapping) carry meaningful silent-incorrectness risk if implemented without explicit resolution; the other three carry lower or self-revealing risk.** This is a reason to resolve them before WP-005/implementation, not a reason the Specification itself is unsound.

### 6. Gap Validation

Confirming, for each of WP-003 §9's five items, that the taxonomy correctly categorizes it and that closing it requires only a decision within the already-defined categories — **not** a change to the Specification itself:

| Gap | Taxonomy Category (already defined, WP-003) | Scope of Blockage | Spec Change Needed to Close It? |
|---|---|---|---|
| 1. `WorkforceWorkerAdapter.supports()` | Ambiguous Mapping (§3) | Narrow — only this one adapter's `.supports()` method | No — resolving means picking one of the two already-named candidates within the existing category |
| 2. `ManufacturingWorkerAdapter.worker_id` | Synthesized Identity (§4) | Narrow — only this one adapter's identity generation | No — resolving means choosing a generation method meeting the already-stated invariants (unique, stable, string) |
| 3. `ManufacturingWorkerAdapter.supports()` | Absent Mapping (§3) | Narrow — only this one adapter's `.supports()` method | No — resolving means choosing a default policy for the already-named category |
| 4. `ManufacturingWorkerAdapter.execute()` field mapping | Not a taxonomy category — a data-mapping choice within an otherwise-conforming `execute()` | Narrow — only this one adapter's field translation | No — resolving means confirming or replacing one field-mapping choice |
| 5. `DigitalEmployeeAdapter.execute()` sequencing | Not a taxonomy category — an acceptability confirmation | Narrow — only this one adapter's call sequence | No — resolving means a yes/no confirmation, not a new design |

**No gap requires reopening WP-003. Every gap is narrowly scoped to one adapter's one method, not systemic to the Specification or the Interface Contract as a whole.**

### 7. Overall Validation Verdict

**The Compatibility Specification (WP-003) can be implemented.** Specifically:
- **Fully implementable today, no open gap:** the canonical `EnterpriseWorker`'s native conformance; `OrganizationWorkerAdapter` and `DigitalEmployeeAdapter`'s identity and capability behavior; both `Unsupported Execution` paths (`WorkforceWorkerAdapter`, `OrganizationWorkerAdapter`); every adapter's lifecycle non-modification and error-propagation behavior.
- **Blocked, narrowly, pending Chief Architect decision:** `WorkforceWorkerAdapter.supports()`; all three of `ManufacturingWorkerAdapter`'s open items (`worker_id`, `supports()`, `execute()` field mapping); `DigitalEmployeeAdapter.execute()`'s sequencing confirmation (lowest risk of the blocked items).
- **No blockage is systemic.** Every open gap is confined to one adapter's one method; none invalidates the Interface Contract, the Compatibility Layer's overall shape, or any other adapter.

### 8. Explicitly Out of Scope for WP-004 (carried forward, not touched)

- No gap from WP-002 §4 / WP-003 §9 is resolved here — this WP validates and risk-assesses them, it does not decide them.
- No adapter code was written; the Compatibility Matrix and Validation Matrix are analysis artifacts only.
- `EnterpriseWorker.status` (WP-001 finding) remains a separate, untouched runtime issue.
- No `RUNTIME/*.py`, `WORKFORCE/*.py`, `ORGANIZATION/*.py`, `MANUFACTURING_CENTER/*.py`, or `DIGITAL_EMPLOYEE/*.py` file was read for any purpose other than validation confirmation — none was modified.

---

## Deliverables (WP-001 through WP-004 only)

- This document. No file under `AI5R-SDK`, `PRODUCTS`, or elsewhere was created or modified.

## Definition of Done — WP-004

- Compatibility Matrix, Validation Matrix, Supported Behaviors, Unsupported Behaviors, Risk Assessment, and Gap Validation all produced.
- WP-002's design confirmed consistent with WP-003's specification — no contradiction found.
- Overall verdict rendered: the Specification can be implemented; blockage is narrow and gap-specific, not systemic.
- No implementation, no migration, no runtime modification, no adapter implementation, no Worker changes.
- Nothing committed or pushed.

**WP-004 disposition:** APPROVED ("Excellent validation"). Roadmap adjustment follows below — WP-005 is now Gap Resolution Decision, inserted before Migration Plan.

---

## WP-005 — Gap Resolution Decision

**Strict scope, as instructed:** for each of the five gaps carried forward from WP-002 §4 / WP-003 §9 / WP-004 §6, produce Current State, Possible Options, a Recommended Option, Architecture Impact, and Risk. **The Decision field is deliberately left PENDING in every case** — per the Constitution's Canonical Rule ("If canonical ambiguity appears: STOP. Report. Wait. Do not decide"), a recommendation is offered, but the decision itself belongs to the Chief Architect. No implementation, no migration, no runtime modification, no adapter implementation, no Worker modification, no code.

### Gap 1 — `WorkforceWorkerAdapter.supports()` (Ambiguous Mapping)

| | |
|---|---|
| **Current State** | `Worker.can_handle(required_role, required_skills)` matches on a single `role` string and a `skills` list (confirmed, `worker.py:16-26`). `Worker(Protocol)` requires `supports(task_type: str) -> bool` — a single string, with no authoritative mapping to either `role` or `skills` in the wrapped type's own code. |
| **Possible Options** | **A.** Map `task_type` to `required_role` (`can_handle(required_role=task_type)`). **B.** Map `task_type` to a single required skill (`can_handle(required_skills=[task_type])`). **C.** Match either (`can_handle(required_role=task_type) or can_handle(required_skills=[task_type])`). |
| **Recommended Option** | **B.** The canonical `EnterpriseWorker.supports()` itself is `task_type in self.capabilities` — a flat-list membership check (confirmed, `enterprise_worker.py:24-25`). `Worker.skills` is the closer structural analog to `capabilities` (both flat lists of granular strings); `Worker.role` is closer to `EnterpriseWorker.worker_type` (a single categorical label never matched against `task_type` anywhere in the canonical implementation). Option B keeps the adapter's mapping semantically consistent with how the canonical Worker itself defines "supports." |
| **Architecture Impact** | Confined to this one adapter's `supports()` method. `Worker.role`/`department` remain fully available for other purposes (e.g. a future Migration Plan use case needing role-based filtering) via direct access to the wrapped object — this decision does not remove or hide that data. |
| **Risk** | Medium if left unresolved or resolved incorrectly (per WP-004 §5) — silent mis-routing of tasks to workers whose skills don't actually match, or silent exclusion of qualified ones. Option B directly targets this risk by aligning with capability semantics rather than role semantics. |
| **Decision** | **APPROVED (Chief Architect).** Map `task_type` to skill membership — Option B: `can_handle(required_skills=[task_type])`. |

### Gap 2 — `ManufacturingWorkerAdapter.worker_id` (Synthesized Identity)

| | |
|---|---|
| **Current State** | `ManufacturingWorker` is stateless with no `__init__` override and no identity field of any kind (confirmed, `manufacturing_worker.py:18-23`). The Interface Contract (WP-003 §1) requires `worker_id` be non-empty and stable for the adapter's lifetime. |
| **Possible Options** | **A.** Generate a fresh UUID per adapter construction. **B.** Use a single fixed, deterministic identifier (e.g. `"manufacturing-worker-default"`), reflecting that `ManufacturingWorker()` is always constructed identically today and that `MANUFACTURING_CENTER.ManufacturingRuntime` defaults to exactly one shared instance (confirmed in `ARCH-REVIEW-003` research). **C.** Require the adapter's constructor caller to supply an explicit `worker_id` parameter, with no default synthesis. |
| **Recommended Option** | **B.** `ManufacturingWorker` today has no concept of multiple distinct instances — a fixed id accurately reflects that reality, rather than implying a multiplicity that doesn't exist (Option A, which risks the identity-fragmentation finding in WP-004 §5) or requiring every call site to supply an id for a type that doesn't yet need one (Option C). |
| **Architecture Impact** | Confined to this one adapter. If `ManufacturingWorker` is ever extended to support multiple distinct instances (out of scope here), this identity choice would need revisiting — a forward caveat, not acted on now. |
| **Risk** | Medium if Option A were chosen instead and multiple adapter instances were created over time, each getting a different identity for what is conceptually the same worker (per WP-004 §5). Option B eliminates that specific risk by design. |
| **Decision** | **APPROVED (Chief Architect).** Use a deterministic Worker ID — Option B, refined: a runtime-generated UUID (Option A) is explicitly prohibited, not merely disfavored. The identifier must be fixed and deterministic, not regenerated per construction. |

### Gap 3 — `ManufacturingWorkerAdapter.supports()` (Absent Mapping)

| | |
|---|---|
| **Current State** | `ManufacturingWorker` has no capability/type concept at all — its own docstring and code confirm it "does not execute any business logic... simulates execution" for any well-formed node, unconditionally. |
| **Possible Options** | **A.** Always return `True` (mirrors the wrapped type's actual unconditional-acceptance behavior). **B.** Always return `False` (inert for assignment purposes until a real mechanism exists). **C.** Require an explicit, out-of-band capability declaration supplied at adapter-construction time (e.g. a `declared_task_types: list[str]` parameter), with `supports()` checking membership in that caller-supplied list. |
| **Recommended Option** | **C.** Neither A nor B honestly reflects intent: the wrapped type's unconditional acceptance is an acknowledged placeholder/simulation property (confirmed by its own docstring), not a deliberate "no filtering needed" design decision. Option C avoids both over-matching (A — flagged **High** risk in WP-004 §5, since it would defeat `WorkerAssignmentEngine`'s capability gating entirely for this adapter) and under-matching (B — would make the adapter permanently unusable for assignment). |
| **Architecture Impact** | Adds a new constructor parameter to the **adapter**, not to `ManufacturingWorker` itself — consistent with "no Worker modification," since the parameter lives entirely on the wrapper. |
| **Risk** | **High** if Option A were chosen (per WP-004 §5) — directly undermines `WorkerAssignmentEngine`'s own matching guarantee. Option C avoids this by design, at the cost of requiring an explicit declaration from whoever registers the adapter rather than free default behavior. |
| **Decision** | **APPROVED (Chief Architect) — supersedes the Recommended Option's specific mechanism.** The plain `declared_task_types: list[str]` parameter proposed in Option C is replaced by a named concept, **Capability Descriptor**, which becomes the canonical compatibility representation for `ManufacturingWorker`'s capabilities — not a one-off adapter constructor argument. Option C's underlying principle (an explicit, out-of-band, caller-supplied declaration — never `True`, never `False`) is retained; only its concrete mechanism changes. **Capability Descriptor's internal shape (fields, construction, validation) is not specified by this Decision** and is not invented here — it is reserved for WP-008 (Implementation Plan) or a dedicated design step. |

### Gap 4 — `ManufacturingWorkerAdapter.execute()` Field Mapping (`task_id` → `node_id`)

| | |
|---|---|
| **Current State** | `ManufacturingWorker.execute(node)` requires `node.node_id` — a non-empty string (confirmed, `manufacturing_worker.py:42-45`). `EnterpriseTask` has `task_id` (uuid-derived, non-empty by construction), not `node_id` (confirmed, `enterprise_task.py:16`). |
| **Possible Options** | **A.** Map `task.task_id` directly to the required `node_id`. **B.** Map a different `EnterpriseTask` field (e.g. `task_type` or `title`) to `node_id`. **C.** (Orthogonal to A/B) Construct an explicit small translation object exposing `.node_id` at execute-time, rather than passing `task` itself and relying on attribute-name coincidence. |
| **Recommended Option** | **A, implemented via C's mechanism.** `task_id` is the only `EnterpriseTask` field sharing `node_id`'s structural guarantee (non-empty, unique, uuid-derived) — `title`/`task_type` are caller-supplied free text with no such guarantee (rejects B). Using an explicit translation object (C) rather than passing `task` directly keeps the mapping visible and intentional in the adapter's own code, rather than accidental. |
| **Architecture Impact** | Confined to this one adapter's `execute()` body. No change to `EnterpriseTask` or `ManufacturingWorker`. |
| **Risk** | Low-Medium (per WP-004 §5) — if wrong, fails loudly via `ManufacturingWorker`'s own `ValueError`, not silently. |
| **Decision** | **APPROVED (Chief Architect).** Use an explicit **Translation Object** between `task.task_id` and `node_id` — Option A's mapping, via Option C's mechanism, now mandatory: implicit field mapping (passing `task` directly and relying on attribute-name coincidence) is explicitly prohibited, not merely disfavored. |

### Gap 5 — `DigitalEmployeeAdapter.execute()` Two-Call Sequencing

| | |
|---|---|
| **Current State** | `DigitalEmployee.execute()` takes no task parameter — it reads `self.current_task` (a plain string), set by a prior `self.assign(task: str)` call (confirmed, `digital_employee.py:64-74`). Satisfying `Worker(Protocol)`'s single-call `execute(task)` requires the adapter to call `wrapped.assign(task.task_id)` immediately before `wrapped.execute()`. |
| **Possible Options** | **A.** Accept the two-call sequence inside the adapter's own `execute(task)` method — zero changes to `DigitalEmployee`. **B.** Change `DigitalEmployee.execute()`'s own signature to accept a task parameter directly. **C.** Require the caller to have already called `wrapped.assign()` via some other path before invoking the adapter's `execute()`. |
| **Recommended Option** | **A.** It is the only option consistent with both "no Worker modification" (rules out B, which would edit `DIGITAL_EMPLOYEE` code) and the Interface Contract's single-call `execute(task)` shape (rules out C, which would push sequencing responsibility outside the adapter, contrary to WP-003 §6). It also reproduces `DigitalEmployee`'s own existing `assign()`-then-`execute()` usage pattern exactly (confirmed, `digital_employee.py:64-74`), rather than inventing a new one. |
| **Architecture Impact** | None beyond this one adapter. `DigitalEmployee`'s own class and its other consumers (`DIGITAL_EMPLOYEE`'s own runtime/execution engines) are unaffected. |
| **Risk** | Low (per WP-004 §5) — largely a confirmation of an already-necessary design, not a live open risk. |
| **Decision** | **APPROVED (Chief Architect).** Compatibility Layer performs `assign()` then `execute()` — Option A. `DigitalEmployee` itself remains unchanged; no modification to `DIGITAL_EMPLOYEE` code, ever. |

### Summary

| Gap | Recommended Option | Risk if Unresolved | Decision |
|---|---|---|---|
| 1. `WorkforceWorkerAdapter.supports()` | B — skill-membership | Medium | **APPROVED — skill membership (Option B)** |
| 2. `ManufacturingWorkerAdapter.worker_id` | B — fixed deterministic id | Medium | **APPROVED — deterministic Worker ID; runtime UUID prohibited** |
| 3. `ManufacturingWorkerAdapter.supports()` | C — explicit declared-capability parameter | High | **APPROVED — Capability Descriptor (supersedes Option C's mechanism; shape not yet specified)** |
| 4. `ManufacturingWorkerAdapter.execute()` mapping | A via C — `task_id → node_id` through an explicit translation object | Low-Medium | **APPROVED — explicit Translation Object; implicit mapping prohibited** |
| 5. `DigitalEmployeeAdapter.execute()` sequencing | A — accept the two-call sequence | Low | **APPROVED — `assign()` then `execute()`; `DigitalEmployee` unchanged** |

**All five gaps now carry a Chief Architect Decision.** Gaps 1, 2, 4, and 5 adopt their Recommended Option as-decided. Gap 3's Decision supersedes its Recommended Option's specific mechanism (a plain list parameter) with a named concept, Capability Descriptor, whose own internal shape remains unspecified and is not invented here.

### Compatibility Principle (Chief Architect Decision, applies platform-wide to the Compatibility Layer — not scoped to any single gap)

> **The Compatibility Layer may translate Identity, Capability, and Execution — but shall never change Business Meaning.**

This formalizes and names a constraint already implicit throughout WP-003 (§2 "introduces zero new states," §6 "never implement new business logic," §8 "no side effects beyond the wrapped object's own"), and now governs every adapter and every future Decision in this MWO, not only the five above:

- **Identity** may be translated (passed through natively, or — per Gap 2 — synthesized deterministically where the wrapped type has none of its own).
- **Capability** may be translated (per Gap 1's skill-membership mapping, Gap 3's Capability Descriptor, or the already-clean Direct Mappings for `OrganizationWorkerAdapter`/`DigitalEmployeeAdapter`).
- **Execution** may be translated (per Gap 4's explicit Translation Object, Gap 5's `assign()`-then-`execute()` sequencing).
- **Business Meaning** — what the wrapped legacy type actually *does*, and why — may never be changed by any adapter, translation, or sequencing choice. An adapter is a shape-conforming wrapper, never a reinterpretation of the wrapped type's own behavior.

### Explicitly Out of Scope for WP-005

- All five gaps now carry a Decision (this update) — no gap remains unresolved.
- No adapter code was written; these remain Decisions, not implementations.
- `EnterpriseWorker.status` (WP-001 finding) remains a separate, untouched runtime issue.
- No `RUNTIME/*.py`, `WORKFORCE/*.py`, `ORGANIZATION/*.py`, `MANUFACTURING_CENTER/*.py`, or `DIGITAL_EMPLOYEE/*.py` file was modified.

---

## Deliverables (WP-001 through WP-005 only)

- This document. No file under `AI5R-SDK`, `PRODUCTS`, or elsewhere was created or modified.

## Definition of Done — WP-005

- Current State, Possible Options, Recommended Option, Architecture Impact, and Risk produced for all five gaps.
- Every Decision field now carries an explicit Chief Architect Decision — none inferred or resolved unilaterally by the Implementation Engineer.
- One platform-wide Compatibility Principle added by Chief Architect Decision (Identity/Capability/Execution may translate; Business Meaning may never change).
- No implementation, no migration, no runtime modification, no adapter implementation, no Worker modification, no code.
- Nothing committed or pushed.

**WP-005 disposition:** **APPROVED.** All five gaps decided by the Chief Architect; one Compatibility Principle added. WP-006 (Migration Plan) may now be completed.

---

WP-005 complete — all five Decisions made, Compatibility Principle added. Continuing with WP-006 (Migration Plan), planning only, per instruction.

---

## WP-006 — Migration Plan

**Strict scope, as instructed:** with all five WP-005 gaps now Decided, complete the Migration Plan. **Planning only.** No migration, no implementation, no runtime modification, no adapter implementation, no Worker modification, no code — every item below is a plan, not an executed action.

### 1. Migration Principles

Principles 1–3 restated unchanged from the prior template (WP-002–WP-004 properties). Principles 4–5 updated to reflect WP-005's completion; Principle 6 added per the new Compatibility Principle.

1. **No wrapped legacy class is ever modified**, at any point in any phase (WP-003 §6, reaffirmed; unconditional).
2. **No canonical orchestration file** (`WorkerAssignmentEngine`, `TaskExecutionEngine`, `MissionRuntime`) **is modified** to accommodate any specific adapter — adapters conform to the existing canonical Interface Contract (WP-003 §1); the contract does not bend to fit an adapter (unconditional).
3. **Migration proceeds one legacy Worker concept at a time**, never in bulk — so any single concept's migration can be evaluated, paused, or rolled back independently of the other three (unconditional).
4. **Every gap that previously blocked an adapter now has a Chief Architect Decision (WP-005).** An adapter may proceed to implementation (WP-008) only once its own Decision(s) are reflected exactly as decided — no adapter-author judgment call substitutes for or "improves on" a recorded Decision, including Gap 3's still-unspecified Capability Descriptor shape (§4 below).
5. **This Plan (WP-006) does not itself authorize implementation.** WP-007 (Deprecation Strategy) and WP-008 (Implementation Plan) remain separately gated, each requiring its own Chief Architect approval, per the roadmap.
6. **Compatibility Principle (WP-005):** the Compatibility Layer may translate Identity, Capability, and Execution, but shall never change Business Meaning. This governs every adapter's implementation (WP-008) and every validation criterion in §6 below.

### 2. Migration Phases

| Phase | Definition | Status |
|---|---|---|
| **Phase 1 — Canonical Promotion** | Identify and confirm the canonical Worker type and contract. | **COMPLETE** — WP-001, APPROVED. `EnterpriseWorker` / `Worker(Protocol)` confirmed as canonical. |
| **Phase 2 — Compatibility Layer** | Design (WP-002), formally specify (WP-003), and validate (WP-004) a non-invasive adapter layer. | **COMPLETE at the decision level.** WP-002–WP-005 all APPROVED; all five gaps Decided. Adapter *code* does not exist yet — implementation is WP-008's scope, gated on this Plan's own approval. |
| **Phase 3 — Gradual Migration** | For each legacy Worker concept: implement its adapter (per WP-002 design + WP-003 specification + WP-005 Decisions), register it into `WorkerAssignmentEngine` alongside — not in place of — the legacy type's existing direct usage, and confirm it behaves per the Interface Contract (WP-003 §1) before any consumer is switched to route through it. One legacy concept migrates at a time (Principle 3). | **NOT STARTED — decision-level entry criteria now MET for all four concepts** (§4 below). Actual implementation remains gated on **WP-008 (Implementation Plan) approval**, not yet begun, and — for `ManufacturingWorkerAdapter` specifically — on Capability Descriptor's shape being defined (§4). |
| **Phase 4 — Retirement** | Once a legacy Worker concept's consumers have all migrated to its canonical adapter (Phase 3 complete for that concept) and no direct caller of the legacy type remains, remove the legacy direct-usage path — concrete mechanics reserved for **WP-007 — Deprecation Strategy**, not yet started. | **NOT STARTED.** Entry condition: Phase 3 complete for the concept in question. WP-007's own content is not specified by this WP-006. |

### 3. Migration Preconditions

| Precondition | Status |
|---|---|
| WP-001 (Canonical Worker Identification) approved | **MET** — APPROVED |
| WP-002 (Compatibility Layer Design) approved | **MET** — APPROVED |
| WP-003 (Compatibility Specification) approved | **MET** — APPROVED |
| WP-004 (Compatibility Validation) approved | **MET** — APPROVED ("Excellent validation") |
| WP-005 (Gap Resolution Decision) — explicit Decision for all five gaps | **MET** — APPROVED, all five gaps Decided, Compatibility Principle added |
| This WP-006 Migration Plan itself approved by the Chief Architect | **NOT YET MET** — produced now, awaiting its own disposition, per the "one WP at a time, stop after each WP" instruction |
| No canonical orchestration file modified outside an approved WP-008 | **MET as of this document** — zero modifications performed by WP-001–WP-006 |
| Capability Descriptor's concrete shape defined (blocks `ManufacturingWorkerAdapter` implementation specifically, per Gap 3's Decision) | **NOT MET** — named and scoped by Gap 3's Decision, but its fields/construction are not specified; reserved for WP-008 or a dedicated design step |
| WP-007 (Deprecation Strategy) approved | **NOT STARTED** |
| WP-008 (Implementation Plan) approved | **NOT STARTED** |

### 4. Migration Matrix

| Legacy Worker | ↓ Canonical Worker (via) | Decision | Status |
|---|---|---|---|
| `WORKFORCE.Worker` | `EnterpriseWorker` (via `WorkforceWorkerAdapter`) | **APPROVED** — `.supports()` maps `task_type` to skill membership (Gap 1) | Decision-ready. `.worker_id` already Native/clean (WP-004 §3); `.execute()` is confirmed permanent Unsupported Execution (WP-003 §7), not blocked. No further gap. |
| `ORGANIZATION.OrganizationWorker` | `EnterpriseWorker` (via `OrganizationWorkerAdapter`) | **No Decision required** — WP-004 §3 found no blocking gap for this concept | Decision-ready. `.worker_id`, `.supports()` both Native/Direct and already clean; `.execute()` is confirmed permanent Unsupported Execution. |
| `MANUFACTURING_CENTER.ManufacturingWorker` | `EnterpriseWorker` (via `ManufacturingWorkerAdapter`) | **APPROVED** — deterministic `worker_id`, never a runtime UUID (Gap 2); Capability Descriptor replaces the declared-parameter mechanism for `.supports()` (Gap 3); explicit Translation Object for `task_id → node_id`, implicit mapping prohibited (Gap 4) | **Decided, not yet implementation-ready** — Capability Descriptor's own shape is undefined (§3 above); Gaps 2 and 4 have no remaining open question. |
| `DIGITAL_EMPLOYEE.DigitalEmployee` | `EnterpriseWorker` (via `DigitalEmployeeAdapter`) | **APPROVED** — `assign()` then `execute()`; `DigitalEmployee` itself unchanged (Gap 5) | Decision-ready. `.worker_id`, `.supports()` both Native/Direct and already clean. |

### 5. Rollback Strategy

- Because no adapter ever modifies its wrapped legacy class (Principle 1), and no canonical orchestration file is modified to accommodate any specific adapter (Principle 2), rolling back any single concept's migration is structurally equivalent to deregistering (or never registering) that concept's adapter instance from `WorkerAssignmentEngine`. The legacy type's own behavior is unaffected either way, for all four concepts, regardless of which gap(s) applied to it.
- Because an adapter holds no lifecycle or mutable state of its own beyond the single wrapped reference (WP-003 §2), rollback requires no data migration, no schema change, and no reversal of wrapped-object state — for all four concepts.
- **`WorkforceWorkerAdapter` / `OrganizationWorkerAdapter` / `DigitalEmployeeAdapter`:** rollback is deregistration only — no adapter-owned state exists to unwind for any of the three, per the above.
- **`ManufacturingWorkerAdapter`:** rollback is likewise deregistration only. One caveat specific to Gap 2's deterministic identity: because `worker_id` is fixed rather than freshly generated per instance, re-registering after a rollback reproduces the identical identifier — this is a deliberate consequence of Gap 2's Decision (avoiding the identity-fragmentation risk WP-004 §5 flagged for Option A), not a new rollback risk.
- Rollback triggers (what condition causes a rollback to be initiated) are an **operational, not architectural, decision** and are not specified by this Plan — reserved for WP-008 or operational runbooks once implementation exists to observe.

### 6. Migration Validation

- Structural validation approach: confirm each implemented adapter satisfies the Interface Contract (WP-003 §1), as already validated at the design level in WP-004 §2 (Validation Matrix, 8/8 PASS), plus the new Compatibility Principle (§1 Principle 6) — no adapter's translation of Identity/Capability/Execution may alter its wrapped type's Business Meaning.
- Per-adapter acceptance criteria, now decidable given WP-005's Decisions:
  - **`WorkforceWorkerAdapter.supports(task_type)`** must return `True` if and only if `task_type` appears in the wrapped `Worker.skills` list (Gap 1) — verified against `Worker.can_handle`'s own existing skill-matching behavior, not a new algorithm.
  - **`OrganizationWorkerAdapter`**: no new criteria beyond WP-003 §1 — already Direct/Native, no Decision was required.
  - **`ManufacturingWorkerAdapter.worker_id`** must be identical across every call and every adapter instance wrapping the module's single shared `ManufacturingWorker` (Gap 2) — verified as a fixed, non-regenerating value, never a fresh UUID.
  - **`ManufacturingWorkerAdapter.supports(task_type)`** must consult a Capability Descriptor supplied at adapter-construction time (Gap 3) — the specific assertion (what a Descriptor must contain, how membership is checked) **cannot be finalized until Capability Descriptor's shape is defined** (§3 precondition, not yet met).
  - **`ManufacturingWorkerAdapter.execute(task)`** must derive `node_id` only via an explicit Translation Object from `task.task_id` (Gap 4) — verified that no implicit/attribute-coincidence mapping path exists in the adapter's code.
  - **`DigitalEmployeeAdapter.execute(task)`** must call `wrapped.assign(task.task_id)` immediately before `wrapped.execute()`, in that order, exactly once each (Gap 5) — verified against `DigitalEmployee`'s own existing `assign()`→`execute()` usage pattern, and that no `DIGITAL_EMPLOYEE` file was modified to achieve it.
- **Regression scope**: for every adapter, existing consumers of the wrapped legacy type via its own direct API (not through the adapter) must show zero behavioral change — the adapter is additive, not a replacement, until Phase 4 (Retirement) for that concept.

### 7. Definition of Done — WP-006

- All seven required sections (Migration Principles, Migration Phases, Migration Preconditions, Migration Matrix, Rollback Strategy, Migration Validation, this section) completed with the Chief Architect's WP-005 Decisions applied.
- Every Migration Matrix Decision field reflects the actual Decision recorded in WP-005 — none re-derived, reinterpreted, or extended beyond what WP-005 states (Capability Descriptor's shape explicitly left undefined, not filled in).
- Compatibility Principle (Identity/Capability/Execution may translate; Business Meaning may never change) incorporated into Migration Principles and Migration Validation.
- No migration, no implementation, no runtime modification, no adapter implementation, no Worker modification, no code.
- No Completion Report, no Engineering Audit, no Repository Audit produced — per instruction, reserved for later.
- Nothing committed or pushed.

---

**WP-006 disposition:** **APPROVED** ("Planning PASS. Architecture PASS. Migration Strategy PASS. The Worker Promotion architecture is now sufficiently specified.").

**Phase Transition (Chief Architect directive):** This workstream moves from **Planning** to **Manufacturing**. No further planning work package is authorized under this MWO unless a future implementation blocker is discovered — in which case a narrowly-scoped planning addendum addressing only that blocker may be raised, not a general reopening of planning. All remaining roadmap items (WP-007 Deprecation Strategy, WP-008 Implementation Plan) are Manufacturing-phase: implementation, testing, audit, and migration. Current priority remains LTSA v1.0 delivery.

---

Stopping here. WP-006 APPROVED, planning phase closed. No implementation, testing, audit, or migration has begun. Waiting for separate, explicit Implementation Approval before any Manufacturing-phase work on this MWO begins.
