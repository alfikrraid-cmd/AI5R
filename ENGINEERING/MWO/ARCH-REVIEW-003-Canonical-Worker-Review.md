# ARCH-REVIEW-003 — Canonical Worker Review

Status: **FROZEN.** Chief Architect review verdict: Research PASS · Analysis PASS · Decision PASS · Architecture PASS · Documentation PASS. `ADR-AR-003` (Option A' — Canonical Promotion Strategy) is the final, frozen disposition of this Review. No implementation has been performed. This document (research, comparison, Decision record) does not reopen absent a new Chief Architect directive.
Raised by: `MWO-PLT-002` WP-000 §6 (Universal Worker Protocol / UWP-001 research), elevated by explicit Chief Architect directive — **not** classified as ordinary Technical Debt.
Category: Architecture Review Required — a live Canonical Rule question (`CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md`: *"There must be exactly ONE canonical implementation... If canonical ambiguity appears: STOP. Report. Wait. Do not decide"*) — resolved by `ADR-AR-003`.
Scope: Inventory, comparison, decision-option deepening, and Architecture Decision recording — complete and frozen. No file was created or modified under `AI5R-SDK`, `PRODUCTS`, or anywhere else in producing this Review. No implementation, Compatibility Layer, migration, or retirement may begin until separate, explicit Implementation Approval for each of §5's four phases — freezing this Review is not that approval.

---

## Why This Is an Elevated Architecture Review, Not Ordinary Technical Debt

Five independently-built implementations of the same underlying concept — an executor that is assigned work by capability, runs it, and reports status — coexist today in five different subsystems, sharing no common base type. This is not a single duplicated file or a naming collision confined to one corner of the platform (contrast `ARCH-REVIEW-002`'s two-class `ManufacturingEvent` collision, itself already inert/dormant). It is a platform-wide pattern spanning `WORKFORCE`, `RUNTIME`, `ORGANIZATION`, `MANUFACTURING_CENTER`, and `DIGITAL_EMPLOYEE`, each with live consumers depending on its own subsystem's current shape. Deciding how (or whether) to converge these five is a decision about which subsystems change, in what order, and at what risk — squarely a Chief Architect-level Architecture Decision, not something this research resolves or that should be decided inside an ordinary debt-paydown pass.

---

## 1. Full Inventory

| # | Concept | File | Fields (identity/role/capability shape) | Status Field |
|---|---|---|---|---|
| A | `Worker` | `AI5R-SDK/WORKFORCE/worker.py:6` | `worker_id`, `name`, `role`, `department`, `skills: list[str]`, `capabilities: list[str]`, `experience` | `status="AVAILABLE"` |
| B | `EnterpriseWorker` + `Worker(Protocol)` | `AI5R-SDK/RUNTIME/enterprise_worker.py:10`, `task_execution_engine.py:6-8` | `worker_type`, `name`, `capabilities: List[str]`, `priority`, `department`, `worker_id` (uuid), `metadata` | `status="idle"` |
| D | `OrganizationWorker` | `AI5R-SDK/ORGANIZATION/organization_worker.py:8` | `organization_id`, `worker_code`, `worker_name`, `worker_type`, `department_id`, `capabilities: Dict[str, Any]` | `status="ACTIVE"` (fixed) |
| E | `ManufacturingWorker` | `AI5R-SDK/MANUFACTURING_CENTER/manufacturing_worker.py:18` | none (stateless) | none |
| F | `DigitalEmployee` family | `AI5R-SDK/DIGITAL_EMPLOYEE/{digital_employee,employee_capability,employee_runtime*,employee_execution}.py` | `capabilities: list[str]` (`EmployeeCapability`) | `status` with multiple states (see §2 Lifecycle) |
| G (context only, not a Worker) | `EmployeeOrchestrator` | `AI5R-SDK/OSA/EMPLOYEE_ORCHESTRATOR/employee_orchestrator.py` | matches via OSA-local `CapabilityAssignment` (`OSA.CAPABILITY_RESOLVER`, distinct from `AI5R-SDK/CAPABILITY/`) | n/a |

---

## 2. Comparison Across the Requested Axes

### Responsibilities

| Concept | Responsibility |
|---|---|
| A | Track a workforce member's availability, skills, and accumulated experience; gate assignment by role+skill match. Does **not** execute anything itself. |
| B | Represent an enterprise task executor; declare supported task types (`supports()`); optionally implement `execute(task)`. Paired with `WorkerAssignmentEngine` (match by type) and `TaskExecutionEngine` (drive start→execute→complete/fail) and `MissionRuntime` (queue-level orchestration). |
| D | Pure registry record of an organization worker and its declared capabilities (as a bare dict). No assignment gating, no execution, no lifecycle transition of any kind. |
| E | Simulate execution of one node in a local manufacturing execution graph; deterministic, explicitly documented as placeholder/non-business-logic. |
| F | Model a full "digital employee" lifecycle: assignment, execution, self-evaluation, learning, completion, suspension/activation — the richest and heaviest of the five. |
| G | Match a described unit of OSA work to a hardcoded employee via an OSA-local capability-assignment concept — a consumer of "worker-like" matching, not a Worker itself. |

### Lifecycle

| Concept | States | Transitions Enforced By |
|---|---|---|
| A | `AVAILABLE` → `BUSY` → `AVAILABLE` | `Worker.assign()`/`.release()` themselves (raise `ValueError` if misused) |
| B | `idle` → (assignment) → (execution outcome) | **Not enforced by `EnterpriseWorker` itself** — the field exists but no method on the class transitions it; any transition logic lives (if anywhere) in `WorkerAssignmentEngine`/`MissionRuntime`, not confirmed to update `status` in the code read for this review |
| D | `ACTIVE` fixed | Never transitions — no lifecycle at all, a static record |
| E | none | Stateless by design — every call is independent and deterministic |
| F | Richest: working/evaluating/learning/completed/suspended/active | `DigitalEmployee`'s own methods, self-contained |
| G | n/a | n/a |

### Inheritance

No shared base exists across A, B, D, E, F. Each is a bare `@dataclass` or bare `class X:`. The only `typing.Protocol` in this space (`RUNTIME/task_execution_engine.py:6-8`) is structural, local to that one file, and satisfied only by B and by an unrelated `DummyWorker` test double — never referenced by A, D, E, or F. No `abc.ABC`/`@abstractmethod` appears in any Worker-named file repository-wide.

### Dependencies

| Concept | External Dependencies |
|---|---|
| A | stdlib only (`dataclasses`, `typing`) |
| B | `RUNTIME.enterprise_task.EnterpriseTask` only |
| D | stdlib only |
| E | `typing.Any` only |
| F | self-contained (`EmployeeCapability`) |
| G | `OSA.CAPABILITY_RESOLVER.CapabilityAssignment` (OSA-local) |

**None of A, B, D, E, F import anything from `AI5R-SDK/CAPABILITY/` (CP-008) or from `AI5R-SDK/FACTORY` (UMC-001/UMR-001)** — confirmed by repository-wide grep restricted to `*worker*.py` and to the `DIGITAL_EMPLOYEE` tree. The Worker layer, the Capability layer, and the canonical Manufacturing layer are today three fully disconnected code paths.

### Consumers

| Concept | Consumers |
|---|---|
| A | `WORKFORCE/registry.py` (`WorkforceRegistry`), `WORKFORCE/assignment.py` (`WorkAssignmentEngine`/`WorkOrder`/`WorkAssignment`) |
| B | `RUNTIME/worker_assignment_engine.py`, `RUNTIME/mission_runtime.py`, `RUNTIME/task_execution_engine.py` |
| D | `ORGANIZATION/organization_worker_registry.py` |
| E | `MANUFACTURING_CENTER/manufacturing_runtime.py` (its own, locally-named `ManufacturingRuntime`, unrelated to UMR-001) |
| F | `DIGITAL_EMPLOYEE`'s own `employee_runtime_engine.py`/`employee_runtime.py`/`employee_execution.py` |
| G | OSA's own employee-orchestration call sites |

Every concept has at least one real, tested consumer inside its own subsystem — none is dead code. Any convergence strategy must account for migrating or bridging all five consumer sets, not just the five Worker classes themselves.

### Canonical Suitability

| Concept | Suitability Notes |
|---|---|
| A | Strong lifecycle/assignment semantics (`assign`/`release`/`can_handle`), but **no execution method exists at all** — would need one added to serve as a canonical execution protocol. |
| B | The only implementation with a real `execute()` hook, a structural `Protocol`, and an orchestration engine (`WorkerAssignmentEngine` + `TaskExecutionEngine` + `MissionRuntime`) already wired around it — the most "runtime-shaped" of the five. Its default `execute()` raises unconditionally rather than providing a safe no-op default, and its `status` field's transition responsibility is unclear/unconfirmed. |
| D | Weakest candidate — a static data record with no lifecycle and no execution semantics; closer to a directory entry than a Worker. |
| E | Has a real execution method wired to a real (if simulated) runtime, and demonstrates a clean constructor-injection default pattern (`ManufacturingRuntime(worker=None)` defaults to `ManufacturingWorker()`) — but is explicitly, deliberately non-functional placeholder logic, not fit for canonical adoption as-is. |
| F | Richest lifecycle of any concept found, but its states (evaluating/learning/suspended) are employee-specific, not generic-worker-shaped — arguably a specialization built on top of a worker concept, not a candidate base for one. |
| G | Not a Worker; relevant only as a fourth independent "match work to executor by capability" pattern, using a capability concept (OSA-local) that is itself distinct from the platform's own `AI5R-SDK/CAPABILITY/`. |

---

## 3. Options (presented for Chief Architect decision — none selected here)

**Option A — Promote one existing implementation to canonical, migrate the rest onto it.**
Select the most execution-capable existing concept (evidence favors B, `RUNTIME.EnterpriseWorker`/`Worker(Protocol)`, as the only one with a real execution hook and an orchestration engine already built around it) as UWP-001, then migrate `WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, and `DIGITAL_EMPLOYEE` to depend on it in place of their own Worker concept. Consequence: four subsystems' Worker-adjacent code and tests change; B's own gaps (no default lifecycle transition, `execute()` raises rather than no-ops) would need to be resolved as part of promotion, not left as-is.

**Option B — Define UWP-001 as a new, independent protocol; migrate all five onto it.**
Design a canonical shape that no existing implementation fully satisfies today (per §2's Canonical Suitability gaps), then migrate all five subsystems onto it. Avoids favoring any one subsystem's pre-existing design, at the cost of every subsystem changing, including B's already-working orchestration engine.

**Option C — Formalize coexistence; UWP-001 as a thin, optional structural protocol.**
Keep all five as legitimate, subsystem-scoped concepts (Workforce workers, Enterprise task workers, Organization worker records, Manufacturing simulation workers, Digital Employees), and define UWP-001 only as a minimal, optional `typing.Protocol` (formalizing what `RUNTIME/task_execution_engine.py`'s local `Worker(Protocol)` already does, but named and documented at the platform level) that any subsystem MAY choose to satisfy for cross-subsystem interoperability. No subsystem is required to migrate; no existing code changes. Closest to codifying the status quo rather than resolving it.

No option is selected, recommended, or ranked by this document. Each carries a different migration cost (A: 4 subsystems change; B: 5 subsystems change; C: 0 subsystems change) and a different degree of true canonicalization (A/B converge to one type; C leaves five types in place, connected only by an optional structural contract).

---

## 4. Architecture Decision Options — Detailed (research deepening only; still none selected)

Per Chief Architect direction to continue researching without implementing, migrating, unifying, or refactoring, each option from §3 is expanded below to decision-ready form: consequences, risk, consistency with existing platform patterns, and migration scope. This section adds analysis; it does not change, narrow, or rank the three options.

### Option A — Promote `RUNTIME.EnterpriseWorker`/`Worker(Protocol)` to canonical

| Dimension | Detail |
|---|---|
| **What changes** | `WORKFORCE.Worker`, `ORGANIZATION.OrganizationWorker`, `MANUFACTURING_CENTER.ManufacturingWorker`, and the `DIGITAL_EMPLOYEE` family would each need to either be replaced by, or made to wrap/adapt to, `EnterpriseWorker`'s shape (`worker_type`, `capabilities: List[str]`, `status`, `execute(task)`). |
| **Consequences — Positive** | Reuses the one implementation that already has a real execution hook, a structural `Protocol`, and an orchestration engine (`WorkerAssignmentEngine`+`TaskExecutionEngine`+`MissionRuntime`) proven by its own test suite. Least net-new code among the two "converge to one type" options, since the runtime scaffolding already exists. |
| **Consequences — Negative** | `EnterpriseWorker.execute()` currently raises `NotImplementedError` unconditionally rather than offering a safe default — promoting it as-is would propagate that failure mode platform-wide unless resolved first. Four subsystems' tests (`test_workforce_core.py`, `test_organization_worker_registry.py`, `test_manufacturing_worker.py`, the `DIGITAL_EMPLOYEE` suite) would need rewriting against a shape none of them was written for — notably A's `assign()`/`release()`/`can_handle()`/`add_experience()` lifecycle and F's rich state machine (evaluating/learning/suspended) have no equivalent in B today and would need to be added to it, which is itself new design work, not a mechanical migration. |
| **Risk** | Medium-high. `status` transition responsibility in B is unconfirmed/unclear even today (§2 Lifecycle) — promoting an under-specified lifecycle to platform-canonical risks carrying that ambiguity forward into every subsystem that migrates onto it. |
| **Consistency with existing platform patterns** | Matches the precedent set by UMR-001 (`MWO-LTSA-049`): "promote one existing implementation, extend it, do not build new" — Chain A was selected over Chains B/C/D on comparable reasoning (already built around the right domain concepts). This is the same shape of decision, one layer down. |
| **Migration scope** | 4 subsystems (`WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE`) plus their test suites; `RUNTIME` itself is extended, not migrated. |

### Option B — Define a new, independent UWP-001; migrate all five onto it

| Dimension | Detail |
|---|---|
| **What changes** | A protocol is designed from scratch, satisfying no existing implementation exactly, covering the union of behaviors found across A/B/D/E/F (typed capability declaration, a safe-default execution method, a defined lifecycle vocabulary, event publication). All five subsystems, including `RUNTIME`, migrate onto it. |
| **Consequences — Positive** | No subsystem's pre-existing design is privileged over another's — avoids the appearance (or reality) of one team's implementation "winning" by accident of having been built first or most completely. Can be designed to close every gap found in §2's Canonical Suitability row (typed capabilities, safe execution default, one lifecycle vocabulary, event publication) rather than inheriting any one implementation's specific gaps. |
| **Consequences — Negative** | Highest total migration cost — 5 subsystems change, including `RUNTIME`'s already-working `WorkerAssignmentEngine`/`TaskExecutionEngine`/`MissionRuntime`, which today has no defect motivating its own replacement. Design risk: an untested, newly-designed protocol carries more unknowns than extending a proven one (contrast Option A, which reuses B's already-tested orchestration engine). |
| **Risk** | Highest of the three. New design + full-platform migration is the largest surface area for regressions, and mirrors the exact pattern the Constitution's Golden Rules caution against ("Architecture is frozen... never redesign it... unless explicitly requested") unless the Chief Architect explicitly intends a redesign here rather than a promotion. |
| **Consistency with existing platform patterns** | Diverges from the UMR-001 precedent (which explicitly rejected building a new runtime in favor of extending Chain A). Would be a deliberate departure from that precedent, not an application of it — worth naming explicitly since it is the more expensive path chosen over a demonstrated cheaper one. |
| **Migration scope** | 5 subsystems (`WORKFORCE`, `RUNTIME`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE`). |

### Option C — Formalize coexistence via a thin, optional structural protocol

| Dimension | Detail |
|---|---|
| **What changes** | Nothing in any subsystem's existing code. `RUNTIME/task_execution_engine.py`'s local `Worker(Protocol)` is named, documented, and relocated (per the Platform Artifact placement rule established by `MWO-PLATFORM-001`: canonical platform artifacts live under `AI5R-SDK/PLATFORM/`, not `ENGINEERING/`) as `UWP-001`, describing only the minimal shape (`execute(unit_of_work) -> result`) any subsystem MAY choose to satisfy. |
| **Consequences — Positive** | Zero migration risk — no subsystem's tested code changes. Fastest to establish. Gives future Worker-adjacent work (a sixth, seventh implementation) a named, documented target to conform to voluntarily, without forcing retrofitting of the five that already exist. |
| **Consequences — Negative** | Does not resolve the underlying finding — five incompatible Worker shapes remain, un-converged, indefinitely. A caller wanting to treat any "Worker" polymorphically (e.g. a future platform-wide worker registry or dashboard) still cannot do so without subsystem-specific adapters, since D and A have no `execute()` at all and would not satisfy even this thin protocol without their own changes. Lowest actual canonicalization of the three options. |
| **Risk** | Lowest of the three, but carries a different kind of risk: formalizing coexistence could be read as tacitly abandoning the Canonical Rule for this specific finding rather than resolving it, if not paired with an explicit statement of why five implementations are being permitted to remain (unlike Chains B/C/D in `MWO-LTSA-049`, which serve genuinely different purposes — per §"Why This Is an Elevated Architecture Review" above, these five do not). |
| **Consistency with existing platform patterns** | Parallels ACL-001's own explicit design restraint ("ACL-001 contains no runtime logic... no implementation logic") — a precedent exists in this platform for thin, non-invasive specifications. However, ACL-001 is thin by design because it deliberately delegates execution to UMR-001; Option C would be thin by default, with no equivalent single execution authority backing it. |
| **Migration scope** | 0 subsystems change. Only a naming/documentation/relocation action on already-existing code. |

**Summary comparison (deepened, still unranked):**

| | Migration Scope | Consistency w/ Prior Precedent | Risk | Resolves the Finding? |
|---|---|---|---|---|
| **A** | 4 subsystems | Matches UMR-001 precedent (promote-and-extend) | Medium-high | Yes — converges to one type |
| **B** | 5 subsystems | Diverges from UMR-001 precedent (new build) | Highest | Yes — converges to one type, cleanest fit but most expensive |
| **C** | 0 subsystems | Echoes ACL-001's restraint, but without ACL-001's UMR backing | Lowest | No — formalizes coexistence, does not converge |

---

## 5. Architecture Decision — Option A' (Canonical Promotion Strategy)

**Decision recorded. Status: Chief Architect has approved this direction; final Architecture Approval of this written record is still pending confirmation. No implementation has been performed.**

**Option A' is explicitly not Option A as documented in §3/§4.** It selects the same canonical target — `RUNTIME.EnterpriseWorker` / `Worker(Protocol)` (`AI5R-SDK/RUNTIME/enterprise_worker.py`, `task_execution_engine.py`) — but replaces Option A's single-step "promote and migrate the rest" with a four-phase evolutionary strategy, explicitly modeled on the pattern already established by `UMR-001` (`MWO-LTSA-049`: extend Chain A in place, rename Chains B/C/D without touching them, no forced migration of anything not ready).

### Difference from Original Option A

| | Original Option A (§3/§4) | Option A' (this Decision) |
|---|---|---|
| Migration timing | Immediate — `WORKFORCE`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE` migrate onto the canonical Worker as part of the same change | Deferred — no subsystem migrates until its own Compatibility Layer is proven |
| Compatibility | Not addressed | A Compatibility Layer is introduced first, so existing subsystems keep working unmodified while the canonical Worker is established |
| Retirement of the other four | Implicit, immediate, part of promotion | Explicit, last, gated on successful migration — not attempted until migration is proven |
| Risk profile | Medium-high (per §4) — four subsystems' tests change in the same step as promotion | Lower and staged — each phase is independently reversible before the next begins |

### The Four Phases (decision record only — none executed)

1. **Promote.** `RUNTIME.EnterpriseWorker` / `Worker(Protocol)` is designated the canonical Worker (UWP-001). No other subsystem's code changes in this phase.
2. **Maintain Compatibility.** A Compatibility Layer is introduced so `WORKFORCE.Worker`, `OrganizationWorker`, `ManufacturingWorker`, and the `DIGITAL_EMPLOYEE` family continue operating unchanged against the canonical Worker underneath, without their own consumers being touched.
3. **Migrate Gradually.** A Migration Plan is prepared and executed **only after** the Compatibility Layer is proven — each of the four subsystems moves onto the canonical Worker on its own schedule, not as a single platform-wide cutover.
4. **Retire Last.** A Deprecation Strategy for each subsystem's own original Worker implementation is prepared and executed **only after** that subsystem's migration has succeeded — retirement is never attempted ahead of, or concurrently with, migration.

**Explicitly not done by this record:** no Compatibility Layer, Migration Plan, or Deprecation Strategy has been designed or written — this section records the decision and its phase structure only, per instruction ("Do not implement. Update ARCH-REVIEW-003 only."). Each phase becomes its own future work order, requiring its own separate Implementation Approval before it begins; approval of this Decision record is not implementation approval for any phase.

---

## 6. Architecture Decision Record

```
Decision ID:        ADR-AR-003
Decision:           Option A' — Canonical Promotion Strategy
Decision Date:      2026-07-15
Decision Authority:  Chief Architect
```

**Decision Summary:**

AI5R adopts Canonical Promotion as the default strategy whenever multiple implementations of the same platform concept exist.

The preferred implementation shall be promoted to Canonical.

Compatibility shall be maintained.

Migration shall be gradual.

Retirement shall occur only after successful migration.

No immediate replacement or destructive rewrite is permitted.

**Scope of this Decision:** `ADR-AR-003` is recorded here, inside `ARCH-REVIEW-003`, because this Worker finding is what raised it — but its Decision Summary is stated as a platform-wide default, not scoped to Workers alone. It governs how this specific finding is resolved (§5's four phases) **and** stands as the general default AI5R applies the next time multiple implementations of one platform concept are found, unless a future Chief Architect decision states otherwise for a specific case. This is consistent with, and formalizes as policy, the same approach already taken de facto for UMR-001 (`MWO-LTSA-049`: promote Chain A, rename rather than replace Chains B/C/D).

---

## Cross-References

- `ENGINEERING/MWO/MWO-PLT-002-Universal-Worker-Protocol.md` — the WP-000 research that first surfaced this finding (§6).
- `ENGINEERING/MWO/ARCH-REVIEW-002-Canonical-ManufacturingEvent.md` — the prior elevated (non-Technical-Debt) Architecture Review in this repository; same category of finding, different scope and severity.
- `ADR/ADR-003-Capability-as-Universal-Execution-Layer.md`, `AI5R-SDK/CAPABILITY/DOCS/CP-008-CAPABILITY-SPECIFICATION.md` — confirmed, in this review, to be unconsumed by any of the five Worker concepts.
- `ENGINEERING/MWO/MWO-LTSA-049-Universal-Manufacturing-Runtime.md` — the promote-and-extend precedent Option A' explicitly models its four-phase strategy on.

---

## Final Review Verdict

| Check | Result |
|---|---|
| Research | PASS |
| Analysis | PASS |
| Decision | PASS |
| Architecture | PASS |
| Documentation | PASS |

**Status: FROZEN.**

---

Stopping here. `ARCH-REVIEW-003` is closed and frozen. `ADR-AR-003` (Option A' — Canonical Promotion Strategy) stands as the final disposition. No Compatibility Layer, Migration Plan, or Deprecation Strategy has been designed; no implementation performed. Each of §5's four phases still requires its own, separate Implementation Approval before it begins — freezing this Review is not that approval.
