# MWO-PLT-002 — Universal Worker Protocol

Status: WP-000 complete. **Implementation NOT approved. Research approved.** The Worker-duplication finding (originally §6) is elevated and now tracked exclusively in `ENGINEERING/MWO/ARCH-REVIEW-003-Canonical-Worker-Review.md` — this MWO does not continue pending that Architecture Decision.
Type: Platform Work Order (Cross-Product Execution Layer — Research/Specification Layer)
Epic: AI5R Platform — canonical execution-unit protocol, parallel in kind to `MWO-LTSA-048` (UMC-001) / `MWO-LTSA-049` (UMR-001)
Role: Implementation Engineer
Architecture: FROZEN — this document proposes research findings only; no file created or modified anywhere in the repository
Foundation: v1.0 — LOCKED, unchanged
Engineering Standard: v1.0 — LOCKED, unchanged
Basis: Direct read of every "Worker"-named class in `AI5R-SDK/` (`WORKFORCE`, `RUNTIME`, `ORGANIZATION`, `MANUFACTURING_CENTER`), the adjacent `DIGITAL_EMPLOYEE` family, `OSA/EMPLOYEE_ORCHESTRATOR`, `ENTERPRISE/*`, `AI5R-SDK/CAPABILITY/*` + `CP-008-CAPABILITY-SPECIFICATION.md`, `ADR-003-Capability-as-Universal-Execution-Layer.md`, `AI5R-SDK/FACTORY/CORE/universal_manufacturing_contract.py` (UMC-001), `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_runtime.py` (UMR-001).
Scope: Research only, per explicit instruction. No file created or modified under `AI5R-SDK`, `PRODUCTS`, or anywhere else.

---

## 1. Existing Worker Inventory

A repository-wide search for `class \w*[Ww]orker\w*` (excluding `node_modules`/`__pycache__`) found matches only under `AI5R-SDK/` — none under `PRODUCTS/`, `ENGINEERING/`, or `CORE-SERVICES/`. Every file the mission named as a reuse target, plus every additional Worker-named class found, was read in full.

| # | Concept | File | Base Class | Fields (identity/role/skill shape) | Execution Method | Tests |
|---|---|---|---|---|---|---|
| A | `Worker` | `AI5R-SDK/WORKFORCE/worker.py:6` | none (`@dataclass`) | `worker_id`, `name`, `role`, `department`, `skills: list[str]`, `capabilities: list[str]`, `experience`, `status="AVAILABLE"` | **None.** Only `can_handle()`, `assign()`, `release()`, `add_experience()` — this Worker never executes anything, it only tracks assignability. | `WORKFORCE/TESTS/test_workforce_core.py` |
| B | `EnterpriseWorker` | `AI5R-SDK/RUNTIME/enterprise_worker.py:10` | none (`@dataclass`) | `worker_type`, `name`, `capabilities: List[str]`, `status="idle"`, `priority`, `department`, `worker_id` (uuid), `created_at`, `metadata` | `execute(task: EnterpriseTask) -> Dict` — **unconditionally raises `NotImplementedError`** in the base class; override-by-convention, not an ABC. | `RUNTIME/TESTS/test_enterprise_worker.py`, `test_mission_runtime.py` (subclasses it) |
| C | `Worker(Protocol)` | `AI5R-SDK/RUNTIME/task_execution_engine.py:6-8` | `typing.Protocol` — **the only Protocol in this space** | (structural only) `execute(task: EnterpriseTask) -> Dict` | Same signature as B; satisfied structurally by `EnterpriseWorker` and by an unrelated `DummyWorker` test double. **Local to this one file** — never imported by A, D, or E. | `RUNTIME/TESTS/test_task_execution_engine.py` |
| D | `OrganizationWorker` | `AI5R-SDK/ORGANIZATION/organization_worker.py:8` | none (`@dataclass`) | `organization_id`, `worker_code`, `worker_name`, `worker_type`, `department_id`, `capabilities: Dict[str, Any]` (plain dict, not an object), `worker_id` (uuid), `status="ACTIVE"` | **None at all** — only `to_dict()`. No `assign`/`release`/`can_handle` either. Pure data record. | `ORGANIZATION/TESTS/test_organization_worker_registry.py` |
| E | `ManufacturingWorker` | `AI5R-SDK/MANUFACTURING_CENTER/manufacturing_worker.py:18` | none | (stateless — no fields) | `execute(node) -> dict` — validates `node.node_id`, then returns a **hard-coded, self-documented simulation** result (`"simulated": True`); explicitly not real business logic (module docstring). | `MANUFACTURING_CENTER/TESTS/test_manufacturing_worker.py` (extensive) |
| F (adjacent, not "Worker"-named) | `DigitalEmployee` family | `AI5R-SDK/DIGITAL_EMPLOYEE/{employee_capability,digital_employee,employee_runtime*,employee_execution}.py` | none | `capabilities: list[str]` (`EmployeeCapability`, same bare-string shape as A/D) | `DigitalEmployee.assign()`/`.execute()`/`.evaluate()`/`.learn()`/`.complete()`/`.suspend()`/`.activate()` — a fourth, independently-built assign→execute→result cycle | Yes, per-file |
| G (adjacent) | `EmployeeOrchestrator` | `AI5R-SDK/OSA/EMPLOYEE_ORCHESTRATOR/employee_orchestrator.py` | none | matches work to a hardcoded employee lookup table via `OSA.CAPABILITY_RESOLVER.CapabilityAssignment` (an **OSA-local** capability concept, distinct from `AI5R-SDK/CAPABILITY/`) | `_select_employee()` — a fifth reimplementation of "match a unit of work to an executor by required capability" | Not verified in this pass |

`AI5R-SDK/ENTERPRISE/{enterprise_kernel,enterprise_manifest}.py` mention "Mission Based Workers" / "EL-003 Worker Registry" only as manifest strings — aspirational documentation-as-code, no executable Worker logic.

---

## 2. Convergence Analysis — Is There Already a Shared Protocol?

**No.** Verified directly:
- Zero of the Worker-named classes (A, B, D, E) inherit from each other, from a common ABC, or from any shared base. Each is a bare `@dataclass` or bare `class X:`.
- The only `typing.Protocol` (C) is local to `RUNTIME/task_execution_engine.py` and is not referenced by A, D, or E.
- No `abc.ABC` / `@abstractmethod` appears in any of the 9 worker-related files (repo-wide grep restricted to `*worker*.py` — zero hits).

**Despite this, the five core implementations (A, B, D, E, and the DigitalEmployee family F) are not genuinely different architectures — they are near-duplicate, independently-built reimplementations of one underlying concept.** Evidence:
- All carry an identity field (`worker_id` / uuid), a role/type field (`role` / `worker_type` / `worker_type` / none), a `capabilities`/`skills` collection of **bare strings or a bare dict — never a typed object**, and (in most but not all) a mutable `status` string with a different vocabulary each time (`"AVAILABLE"/"BUSY"` vs `"idle"` vs `"ACTIVE"` vs none in D).
- Three subsystems (`WORKFORCE`, `RUNTIME`, `MANUFACTURING_CENTER`) plus `DIGITAL_EMPLOYEE` each independently built their own assignment-engine/registry pair (`WorkAssignmentEngine`+`WorkforceRegistry`; `WorkerAssignmentEngine`+in-memory list; `ManufacturingRuntime`+`ManufacturingWorker`; `EmployeeRuntimeEngine`) that all perform the same match-by-capability → mark-busy → execute → mark-free cycle with zero shared code between them.
- This is a different situation from the four Manufacturing "chains" found in `MWO-LTSA-049` — those solved materially different problems (release-artifact generation vs. build-pack scaffolding vs. project scaffolding vs. manufacturing-domain execution). Here, the same problem — "assign a described unit of work to a described executor with capabilities, run it, get a result" — has been solved five separate times.

**This convergence-without-a-shared-type is itself a finding requiring Chief Architect attention, not a decision made here** — see §6.

---

## 3. "ACL-001" — Identification Finding

A repository-wide search for the literal string `ACL-001` (and `\bACL\b`) returns **zero matches anywhere in the repository.** This identifier does not exist as a named artifact today.

The nearest concrete, already-frozen candidate is `AI5R-SDK/CAPABILITY/` (spec: `CP-008-CAPABILITY-SPECIFICATION.md`, Status: **FROZEN v1.0**), formalized at the architecture-decision level by `ADR-003-Capability-as-Universal-Execution-Layer.md` — which itself states the governing distinction "BRAIN decides, Capability executes" and names Capability as the universal execution layer every AI5R product consumes. Verified in code: `CapabilityObject`, `CapabilityEngine`, `CapabilityRegistry`, `CapabilityValidationEngine`, `CapabilityRuntime`, `CapabilityManifest` all exist and are internally self-consistent (`validate → register → execute`, enforced by `CapabilityRuntime`).

**Confirmed: no Worker implementation (A–G) imports or consumes anything from `AI5R-SDK/CAPABILITY/`.** Every `capabilities` field found in §1 is a bare string list or bare dict, never a `CapabilityObject`. This is directly consistent with ADR-003's own "Consequences → Negative" section, which states plainly that none of Capability's eight groups are "confirmed built or wired... their presence here states intent... not current repository state."

**This research proceeds on the assumption that "ACL-001" refers to this Capability layer** (`CAPABILITY/` + `CP-008` + `ADR-003`) — it is the only existing artifact matching the shape of an execution layer a Worker Protocol would plausibly reuse, and its "BRAIN decides, Capability executes" framing is directly adjacent to "a Worker executes a unit of work." **This is a judgment call, not a confirmed fact, and is flagged here for explicit correction before WP-001 begins** — consistent with how `MWO-LTSA-049`'s Chain A selection was flagged for confirmation rather than assumed silently.

> **Correction (post-drafting, evidence-confirmed):** the above assumption is **wrong**. `MWO-PLATFORM-001-AI5R-Command-Language.md` (Platform MWO, Status: FROZEN) subsequently established the real `ACL-001`: **AI5R Command Language** — a natural-language Operating Language (`AI5R-SDK/PLATFORM/ACL/ACL-001-AI5R-Command-Language.md`), grammar `Verb + Target + Optional Context`, commands `Research/Resume/Load/Manufacture/Review/Status/Commit`, each mapping to an existing Constitution §13 workflow phase — not the Capability layer. Per its own §3.1 Canonical Target Space, "Capability" and "Worker" are each their own separate Target Kind, distinct from ACL itself. **This does not change any finding in §1, §2, §4, or §5 of this document** — none of those relied on what ACL-001 actually is, only on whether it was already wired into any Worker (confirmed: it was not, and still is not, since ACL-001 has no execution logic of its own by design — "Execution belongs to UMR"). It only retires the open confirmation request this section originally raised.

---

## 4. UMC-001 / UMR-001 Wiring Status

**Neither is used by any Worker implementation today.** Confirmed by direct read and repository-wide grep:
- `universal_manufacturing_contract.py` (UMC-001) is referenced only in its own package's `__init__.py`, its own test, and the two Resolution interface files — never in any Worker file.
- `FACTORY/FOUNDATION/manufacturing_runtime.py`'s `ManufacturingRuntime` (UMR-001/"Chain A") imports `BuildWorkspace`, `FactoryOrchestrator`, `ManufacturingEvent`, `ManufacturingContext`, `ManufacturingOrder` — none of which appear in any Worker file. The only "ManufacturingRuntime" symbol any Worker touches is `MANUFACTURING_CENTER/manufacturing_runtime.py`'s own, differently-implemented, same-named class (E's caller) — a separate class in a separate module, unrelated to UMR-001.

**The Worker layer and the canonical Manufacturing contract/runtime layer are today entirely disconnected code paths**, consistent with §3's finding that Capability is likewise disconnected from every Worker.

---

## 5. Candidate UWP-001 Shape (research sketch, not a design decision)

Grounded strictly in behavior **already exhibited by at least one existing implementation** — nothing invented — the five implementations collectively already cover these stages, unevenly:

| Candidate Stage | Exists Today? | Where | Executed Consistently? |
|---|---|---|---|
| Worker Identity | Yes | All of A, B, D, E have an id field | Yes, but different field names (`worker_id` vs generated uuid) |
| Worker Capability Declaration | Yes, but untyped | `capabilities`/`skills` as bare strings/dict everywhere | No — never a typed `CapabilityObject` (§3) |
| Capability Matching / Assignment | Yes | A's `can_handle()`, B/C's `WorkerAssignmentEngine.assign()`, D's `find_by_capability()` | Yes, independently, in 3 different implementations |
| Worker Execution | Partial | B/C's `execute(task)`, E's `execute(node)` | **No** — A and D have no execution method at all; B's default raises `NotImplementedError`; E's is a hard-coded simulation |
| Worker Result | Partial | B/C returns `Dict`; E returns a fixed dict shape | No shared result type — each subsystem invents its own dict shape |
| Worker Lifecycle (busy/free) | Yes, inconsistently | A (`AVAILABLE`/`BUSY`), B (`idle`), D (`ACTIVE`, never transitions) | No — three different status vocabularies, D's never changes |
| Event Publication | **No** | Not found in any Worker file | No Worker publishes to `ManufacturingEventBus` or any event mechanism |

This table is presented only to make the size of the gap concrete for Chief Architect review — **it is not a proposal for what UWP-001 should contain.** Per the mission's explicit scope ("No implementation. WP-000 only."), no protocol design decision is made in this document.

---

## 6. Architecture Validation

**One finding was surfaced here for Chief Architect confirmation, consistent with the Constitution's Canonical Rule ("There must be exactly ONE canonical implementation... If canonical ambiguity appears: STOP. Report. Wait. Do not decide"). Per explicit Chief Architect directive, that finding has since been elevated out of this document:**

> **Five independent, structurally-convergent Worker implementations already exist** (`WORKFORCE.Worker`, `RUNTIME.EnterpriseWorker`, `ORGANIZATION.OrganizationWorker`, `MANUFACTURING_CENTER.ManufacturingWorker`, the `DIGITAL_EMPLOYEE` family) — this finding is **no longer tracked here**. It is now the subject of its own dedicated Architecture Review: `ENGINEERING/MWO/ARCH-REVIEW-003-Canonical-Worker-Review.md`, which presents the full Responsibilities/Lifecycle/Inheritance/Dependencies/Consumers/Canonical-Suitability comparison and three unselected resolution Options (A/B/C), awaiting Chief Architect Architecture Decision. `MWO-PLT-002`/UWP-001 work does not continue pending that decision.

> **Separately, resolved:** §3's "ACL-001 = Capability layer" assumption was unconfirmed at drafting time and has since been corrected in §3 itself — `ACL-001` is the AI5R Command Language (`MWO-PLATFORM-001`), not the Capability layer. This does not reopen or affect the Worker finding above.

No other architectural conflict was found. The `EmployeeOrchestrator`'s OSA-local `CapabilityAssignment`/`CapabilityResolver` (distinct from `AI5R-SDK/CAPABILITY/`) is noted in §1(G) so it is not later confused with the platform-level Capability layer, but reconciling that naming collision is outside this research's scope unless the Chief Architect directs otherwise.

---

## 7. UWP-001 Artifact Definition (identifier only — no design yet)

| Field | Value |
|---|---|
| **Artifact ID** | UWP-001 |
| **Artifact Name** | Universal Worker Protocol |
| **Artifact Type** | Canonical Platform Protocol (proposed) |
| **Owner** | AI5R Platform |
| **Prospective Consumers** | `WORKFORCE`, `RUNTIME`, `ORGANIZATION`, `MANUFACTURING_CENTER`, `DIGITAL_EMPLOYEE`, and any future AI5R Worker |
| **Status** | Not yet designed — this document is inventory and gap-finding only |

---

## Deliverables (this document only)

- This WP-000 document. No `AI5R-SDK` file, `PRODUCTS` file, or any other repository file was created or modified in producing it.

## Definition of Done

- WP-000 complete, submitted for approval.
- No implementation performed, no protocol designed.
- Nothing committed or pushed.
- §3 (ACL-001 identification) and §6 (five-implementation convergence finding) both await explicit Chief Architect confirmation before any WP-001 design work may begin.

---

Stopping here. Research complete. No implementation performed. Awaiting Implementation Approval.
