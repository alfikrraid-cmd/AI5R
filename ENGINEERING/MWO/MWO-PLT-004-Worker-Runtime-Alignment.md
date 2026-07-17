# MWO-PLT-004 — Worker Runtime Alignment

Status: **WP-000 APPROVED — Research PASS, Architecture PASS. No implementation approved.** Findings classified and recorded in `TECHNICAL_DEBT.md`: §5 (`MissionRuntime` exception propagation) as **TD-007, HIGH PRIORITY**; §1–§4/§6–§7 (Worker status lifecycle, reservation, recovery, observability, mutual exclusion) as **TD-008, DEFERRED**. Both are explicitly deferred — **Worker Runtime implementation does not begin unless a finding becomes a direct blocker for LTSA v1.0.** Current objective: resume LTSA Manufacturing. This MWO is paused, not closed.
Type: Platform Work Order — research successor to `MWO-PLT-003` (Canonical Worker Promotion), examining how the Canonical Worker's own Runtime should behave post-promotion
Epic: AI5R Platform — Canonical Worker Promotion follow-on research
Role: Implementation Engineer
Architecture: Platform Foundation LOCKED. `ARCH-REVIEW-003` FROZEN. `EnterpriseWorker` confirmed Canonical Worker (`MWO-PLT-003` WP-001). This document analyzes only; it proposes no solution, redesigns nothing, modifies nothing.
Basis: Direct re-read of `AI5R-SDK/RUNTIME/{enterprise_worker,enterprise_task,enterprise_mission,mission_runtime,worker_assignment_engine,task_execution_engine,task_queue}.py` and their test files (`TESTS/test_{mission_runtime,task_execution_engine,worker_assignment_engine,enterprise_worker,enterprise_task,enterprise_mission}.py`); `AI5R-SDK/RUNTIME/runtime_engine.py` and `HARDENING/runtime_guard.py` (read and confirmed unrelated — see §0); repository-wide grep for retry/recovery/observability mechanisms (zero hits).
Scope: Research only. No file under `AI5R-SDK`, `PRODUCTS`, or anywhere else was created or modified. No runtime modification, no Worker modification, no state transition changes, no lifecycle changes.

---

## 0. Scope Boundary — What Is, and Is Not, "Worker Runtime" Here

Confirmed by direct read, so later work does not conflate them: `AI5R-SDK/RUNTIME/runtime_engine.py`'s `RuntimeEngine` (a profile/definition → handler registry executing capability pipelines) and `HARDENING/runtime_guard.py`'s `RuntimeGuard` (a static source-pattern validator — forbidden `eval`/`exec`, empty contracts) are **both unrelated to the Worker orchestration chain** — neither imports nor is imported by `EnterpriseWorker`, `MissionRuntime`, `WorkerAssignmentEngine`, or `TaskExecutionEngine`. This research concerns exactly the four components the mission named, plus their two immediate collaborators (`EnterpriseTask`, `EnterpriseMission`) and `TaskQueue`, which the chain depends on directly.

---

## 1. Worker Lifecycle

**Current Runtime:** `EnterpriseWorker.status` defaults to `"idle"` (`enterprise_worker.py:15`). No method on `EnterpriseWorker` itself transitions it. Confirmed by direct re-read of `worker_assignment_engine.py` and `mission_runtime.py`: **neither reads nor writes `worker.status` anywhere.** `WorkerAssignmentEngine.assign()` selects a worker by `supports()` alone and never marks it unavailable, reserved, or busy — the same `EnterpriseWorker` instance remains eligible for `assign()` to select again on the very next call, regardless of whether its previously-assigned task has finished.

**Desired Runtime (inferred from the object's own field, not decided here):** A `status` field existing on the canonical Worker implies an intended lifecycle — most plausibly `idle → assigned/busy → idle` (mirroring `Worker`'s own legacy analog in `WORKFORCE`, which *does* enforce this: `assign()` raises `ValueError` if not `AVAILABLE`, confirmed `worker.py:28-31`) or `idle → busy → idle/failed`, matching `EnterpriseTask`'s own enforced pattern (see §2).

**Architecture Gap:** The canonical Worker's own `status` field is **decorative** — present in the dataclass, serialized in `to_enterprise_object()` (`enterprise_worker.py:39`), but never load-bearing anywhere in the chain that assigns and executes work through it. No mechanism today prevents `WorkerAssignmentEngine` from selecting the same worker for a second task while a first task assigned to it is still outstanding — this is currently masked only by `MissionRuntime.run()`'s own single-threaded, strictly sequential `while` loop (one task fully processed before the next is dequeued, confirmed `mission_runtime.py:28-41`), not by any actual reservation mechanism in the Worker or the Assignment Engine themselves.

## 2. Worker Status Transition

**Current Runtime:** None exist. Confirmed, zero methods transition `EnterpriseWorker.status` anywhere in `RUNTIME/`.

**Desired Runtime:** `EnterpriseTask` (the object on the *other* side of the same orchestration chain) already has a real, enforced state machine: `created → assigned → running → completed/failed`, each transition method (`assign()`, `start()`, `complete()`, `fail()`) confirmed to exist and — for `start()` — to actively guard against invalid transitions (`raise ValueError("Task can only start from created or assigned status")`, `enterprise_task.py:44-45`). `EnterpriseMission` similarly enforces `created → running`, guarding `start()` (`enterprise_mission.py:39-40`).

**Architecture Gap:** Of the three core objects in this Runtime (`EnterpriseMission`, `EnterpriseTask`, `EnterpriseWorker`), **two have real, guarded lifecycles and one does not.** This is an internal asymmetry within the canonical Runtime itself, not merely a Worker-specific oversight — `EnterpriseWorker` is the outlier against the pattern its own two siblings already establish.

## 3. Assignment Lifecycle

**Current Runtime:** `WorkerAssignmentEngine.assign(task)` performs a linear scan of `self._workers` (a plain list, populated only by `register()`, confirmed `worker_assignment_engine.py:9-13`), returns the **first** worker whose `supports(task.task_type)` is `True`, and calls `task.assign(worker.worker_id)` (which transitions the *task's* status to `"assigned"` — confirmed `enterprise_task.py:39-41` — but touches nothing on the worker). No removal, marking, or reservation of the selected worker occurs.

**Desired Runtime:** Not decided here — but the existence of `Worker.status` (§1) and the guarded pattern already used for `EnterpriseTask`/`EnterpriseMission` (§2) suggests an assignment step that also reserves the worker (transitions it out of `"idle"`) would be structurally consistent with the rest of this Runtime's own design conventions.

**Architecture Gap:** Assignment today is a pure **selection** step, not a **reservation** step — it identifies a candidate without removing that candidate from future candidacy. This is the same gap as §1, viewed from the Assignment Engine's side rather than the Worker's.

## 4. Execution Lifecycle

**Current Runtime:** Fully synchronous, single call in / single result out: `TaskExecutionEngine.execute(worker, task)` calls `task.start()` → `worker.execute(task)` → on success, `task.complete(result)` and return `result`; on any exception, `task.fail(str(exc))` and **re-raise** (confirmed, `task_execution_engine.py:12-22`). No timeout, no cancellation, no retry, no async/await anywhere in this path.

**Desired Runtime:** Not decided here. The mission scopes this as analysis only.

**Architecture Gap:** None distinct from what §5 identifies below — the execution step itself is internally coherent (task status is correctly transitioned on both success and failure paths); the gap is entirely in what happens to the *re-raised* exception one level up, which is §5's subject.

## 5. Failure Lifecycle

**Current Runtime — the most significant finding of this research:** Direct re-read of `mission_runtime.py:28-41` confirms `MissionRuntime.run()`'s task loop wraps the `worker is None` ("no worker available") case in an explicit, graceful branch (`task.fail("No worker available"); results.append(...); continue` — confirmed lines 32-35), but has **no `try`/`except` of any kind around `self.execution_engine.execute(worker, task)`** (line 37). Since `TaskExecutionEngine.execute()` **re-raises** every exception after recording it on the task (`task_execution_engine.py:20-22`, confirmed), any exception raised by `worker.execute(task)` — for *any* registered worker, including the canonical `EnterpriseWorker`'s own default `execute()`, which itself unconditionally raises `NotImplementedError` if not overridden (`enterprise_worker.py:27-30`) — propagates **uncaught** out of `MissionRuntime.run()` entirely. This aborts mission processing mid-loop: the `while not self.queue.empty()` loop never reaches `mission.complete()` (line 43), and the local `results` list accumulated so far is lost with the unwound stack — the mission never returns a report at all in this case, it raises.

**Desired Runtime:** Not decided here — but the "no worker available" branch already demonstrates the Runtime's own author(s) intended *some* task-level failures to be graceful and mission-continuing (`task.fail(...)`, then `continue`). A "worker found but execution raised" failure is handled by a **fundamentally different, inconsistent policy** — total abort — for what is, from the mission's perspective, the same category of event: one task could not be completed.

**Architecture Gap:** A **confirmed asymmetry, not a hypothetical one**: `MissionRuntime` has two distinct, incompatible failure-handling policies for two conditions that are conceptually the same ("this task did not succeed") — one graceful (task fails, mission continues), one catastrophic (mission itself raises, no report produced, remaining queued tasks never processed). No test in `RUNTIME/TESTS/` exercises the "worker execution raises" path through `MissionRuntime.run()` at all (confirmed — `test_mission_runtime.py`'s only test uses a `TestWorker.execute()` that always succeeds); the gap is therefore also **untested**, not merely undocumented.

## 6. Worker Recovery

**Current Runtime:** None exists. Repository-wide grep for retry/requeue/dead-letter/circuit-breaker patterns across `AI5R-SDK/RUNTIME/` returned zero matches. A worker that fails to execute a task has no path back to any "known good" state (compounded by §1/§2 — there is no state to return to, since none was ever left), and the Assignment Engine has no signal that a given worker just failed and might warrant deprioritization, quarantine, or a health check before being selected again.

**Desired Runtime:** Not decided here.

**Architecture Gap:** Total absence of any recovery concept — not a partial or degraded implementation, a complete one. This compounds directly with §5: since a single execution failure can abort the entire mission (§5), and there is no recovery mechanism to fall back to (§6), the current Runtime's only resilience posture is "the mission run either fully succeeds task-by-task or terminates via an unhandled exception."

## 7. Worker Observability

**Current Runtime:** No event bus, logging, or metrics emission exists anywhere in this Runtime chain. `MissionRuntime.run()`'s only observable output is its own returned dict, assembled synchronously and only available if `run()` returns at all (per §5, it may not). Contrast with the platform's own Manufacturing side: `UMR-001` (`AI5R-SDK/FACTORY/FOUNDATION/manufacturing_runtime.py`) publishes real `BUILD_STARTED`/`BUILD_COMPLETED` events through a `ManufacturingEventBus`, and per-station events are captured in each `ManufacturingResult` — a materially more observable design already exists elsewhere on this same platform, one layer over.

**Desired Runtime:** Not decided here.

**Architecture Gap:** Zero observability today for worker assignment, task start, task completion, or task failure as discrete events — only the task/mission objects' own internal `status` fields record what happened, and only if a caller inspects them after the fact (and, per §5, only if `run()` returned at all rather than raising). No equivalent of `ManufacturingEventBus` exists for this Runtime.

---

## Summary — Current Runtime vs. Desired Runtime vs. Architecture Gap

| # | Topic | Current Runtime | Desired Runtime (inferred, not decided) | Architecture Gap |
|---|---|---|---|---|
| 1 | Worker Lifecycle | `status` field exists, never read/written by orchestration | Presumably enforced `idle ↔ busy` per the field's own presence | Decorative status field; no mutual-exclusion mechanism |
| 2 | Worker Status Transition | No transition methods exist | Guarded transitions, matching `EnterpriseTask`/`EnterpriseMission`'s own pattern | Internal asymmetry: 2 of 3 core objects have real lifecycles, one does not |
| 3 | Assignment Lifecycle | Pure selection (first match), no reservation | Selection + reservation | No reservation step exists |
| 4 | Execution Lifecycle | Synchronous, single call in/out, task status correctly transitioned both ways | Not decided | None beyond §5 |
| 5 | Failure Lifecycle | **Two incompatible policies**: "no worker" is graceful; "worker execution raised" aborts the entire mission | Presumably one consistent, graceful policy for both | **Confirmed, untested, significant asymmetry** |
| 6 | Worker Recovery | None — no retry, requeue, or dead-letter of any kind | Not decided | Total absence, compounds with §5 |
| 7 | Worker Observability | No events, logging, or metrics | Not decided | Zero observability; UMR-001 already demonstrates a stronger pattern elsewhere on this platform |

**No solution is proposed for any of the above.** Every gap is stated as a finding, grounded in direct code and test re-read, not assumption. §5 (Failure Lifecycle) is flagged as the most significant — it is the only one confirmed to actually break a currently-working, previously-tested capability (mission-level reporting) under a condition (a worker's `execute()` raising) that is entirely plausible in ordinary operation, not a contrived edge case.

---

## Deliverables

- This document only. No file under `AI5R-SDK`, `PRODUCTS`, or elsewhere was created or modified.

## Definition of Done — WP-000

- All seven research topics addressed with Current Runtime / Desired Runtime / Architecture Gap, grounded in direct code and test re-read.
- No solution proposed for any gap.
- No runtime modification, no Worker modification, no state transition changes, no lifecycle changes.
- Nothing committed or pushed.

---

Stopping here. WP-000 complete — research only. Awaiting Implementation Approval, per instruction: "Stop after WP-000. Wait for approval."
