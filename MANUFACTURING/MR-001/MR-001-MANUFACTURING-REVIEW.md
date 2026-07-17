# MR-001 — Manufacturing Review of MO-001

Status: COMPLETE
Scope: Manufacturing process only — not architecture, not code, not product redesign
Basis: Direct evidence from actually executing MO-001 (OSA Maintenance v0.1) in this session — 69 files manufactured, 11 tracked phases, one real defect found and fixed via genuine execution, one real process mistake made and corrected

---

## Review Areas

### 1. What worked well?

- **Reusing an exact, proven template eliminated design ambiguity entirely.** All four new registries (Asset, Soot Blower, Work Order, Maintenance History) were manufactured by substitution against `BUILD-PACKS/BP-SEAL`'s already-proven shape (Object → conflict-check Create → Detail → List → Update → Delete → TEST via `psql_common.sh`), with zero new architectural decisions required.
- **Documenting a constraint instead of silently working around it.** The polymorphic `(asset_code, asset_type)` reference in Work Order and Maintenance History — needed because four separate registries have no common supertype table — was written down as a stated design limitation in both the Specification and the DDL comments, not silently patched with a fake foreign key or a new supertype table (which would have been new architecture).
- **Attempting real execution wherever the environment allowed it.** The Basic AI Assistant has no external dependency (BRAIN's pipeline is pure Python), so it was actually run rather than only structurally checked — and this caught a real defect (`ValueError: Observation must have source_object_id`) that no amount of code review would have found, since the defect was in how this module's own input was shaped, not in its syntax.
- **Task tracking gave real, checkable progress** across an 11-phase, 69-file order, rather than a single opaque "manufacturing in progress" state.
- **Prior infrastructure investment paid off directly.** `VERIFICATION/run_verification.sh`'s glob-based discovery (`find ... -name "*_test.sh"`, no hardcoded list) absorbed 21 new test scripts with zero modification — a direct, measurable return on MWO-P-006's earlier work.

### 2. What slowed manufacturing?

- **Repetitive, near-mechanical file generation.** Five workflows × four registries = 20 JSON files that differ only by table/field names consumed a large share of this order's total tool calls, for what is conceptually one substitution operation performed four times.
- **A real process mistake: `| head -100` truncated a live verification run mid-execution**, producing a misleadingly "complete-looking" but actually cut-off transcript that had to be discarded and the full run re-launched from scratch — a genuine, avoidable time cost.
- **The standing credential gap** (no `LTSA_TEST_DSN` / `PG*` environment variable in this session, despite a locally reachable PostgreSQL server) blocked genuine Runtime Verification for 6 of 8 modules — not new to this order (documented since MWO-P-006/RV-004), but still a real, recurring cost every order touching these modules has now paid independently.
- **Reference-reading overhead before each new module.** Correctly determining BRAIN's exact `object_id` requirement, or the precise shape of `BP-SEAL`'s conflict-check pattern, required reading real source files in full before writing anything new — necessary per the Evidence Standard, but a genuine time cost repeated per module.

### 3. Which Manufacturing Orders were too large?

MO-001 itself. It bundled six net-new modules of two categorically different kinds — four DB/n8n-backed registries, one aggregation workflow depending on all of them, and one pure-Python module with no external dependency — under a single Release Candidate determination. The order's overall status ended up gated by its weakest-verified pieces (the credential-blocked registries) even though one piece (the AI Assistant) had strictly stronger evidence behind it (real execution, not just structural validation). A single RC label obscured that these six modules do not actually carry equal confidence.

### 4. Which artifacts should have been separated?

- **The Basic AI Assistant** — categorically different (no DB dependency, genuinely executable in this environment) from the other five. It could have been its own Manufacturing Order, cleanly closed with a real PASS, rather than bundled into an order whose overall status was necessarily qualified by other modules' BLOCKER.
- **The Dashboard** — architecturally downstream of every other registry (it aggregates them), and could reasonably be a follow-on order gated on the registries it depends on already existing, rather than manufactured in the same pass as its own dependencies.

### 5. Which Quality Gates were missing?

- **No gate distinguished "structurally validated" from "actually executed."** This distinction existed informally in this order's report but was not a named, mandatory field until now — see the Updated Quality Gate Template below.
- **No gate confirmed a verification run reached its own real completion marker** before its output was treated as informative — this is exactly how the `| head -100` mistake went unnoticed until manually caught.
- **No pre-flight environment-capability check was a named step before attempting Runtime Verification.** `pg_isready` and an environment-variable check were run reactively, in the middle of the order, rather than as a first, explicit Assembly-phase gate.

### 6. Which repository patterns proved reusable?

- **`BUILD-PACKS/BP-SEAL`'s full shape** — Object, conflict-check Create, Detail/List/Update/Delete, TEST via `psql_common.sh` — reused four times with zero redesign. The single strongest evidence point from this order.
- **`VERIFICATION/run_verification.sh`'s discovery-by-glob** — required no modification to absorb 21 new test files.
- **`AI5R-SDK/BRAIN`'s `EnterpriseCognitivePipeline.run(reality_dict)` public interface** — proved genuinely consumable by a product with zero modification to BRAIN itself, the first confirmed case of this across this entire engagement's architecture work (ADR-002/003).

### 7. Which manual steps should become automated?

- **Per-registry file generation** (5 workflows + 5 tests + 1 schema, differing only by substituted names) is now a fully mechanical transformation and should be scripted — reusing `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR`, which MWO-P-001 already found exists but has "no confirmed integration into the other build packs' generation flow." This order is a second, independent data point that such a generator would have real value.
- **Structural validation** (`bash -n`, JSON parse, `py_compile`) was run as hand-typed shell loops this order. It should become one named, reusable script (e.g. `VERIFICATION/structural_validate.sh`) rather than re-typed per order.
- **Verification-run completion checking** — confirming the runner's output actually contains `=== Verification Summary ===` before treating any run as informative — should be automated, not left to manual inspection.

### 8. Which Manufacturing Rules should be updated based on real production experience?

- **Attempt real execution wherever the environment genuinely allows it, even when full verification elsewhere is blocked.** This order's one real defect was found only because execution was attempted for the one module capable of it, despite the DB-side blocker applying to everything else.
- **Every Manufacturing Report must separate "structurally validated" from "actually executed" as two distinct, named fields**, mirroring the Engineering Standard's existing Structural/Runtime Validation split (§8) but stated explicitly at the Manufacturing Order level, not left implicit.
- **Cap new-module count per Manufacturing Order.** A rule such as "one Manufacturing Order manufactures at most N new modules of the same category; additional modules become MO-00X.Y follow-on orders" would directly prevent the bundling issue in Review Area 3.
- **A completed background verification run must be confirmed to have reached its own summary marker before its result is cited** — codifying the lesson from the `head -100` mistake.

---

## Required Output 1 — Lessons Learned

1. A proven pattern, reused exactly, eliminates architectural risk — every new-module decision in MO-001 was a substitution, not a design choice, because `BP-SEAL` already existed as a validated template.
2. Documented constraints (the polymorphic asset reference) are strictly better than silent workarounds or unrequested new architecture — this should remain the default whenever a real design tension is found, not an exception.
3. Real execution finds real defects that structural review cannot — the AI Assistant's `source_object_id` requirement was invisible to `bash -n`/JSON-validity checks and only surfaced by actually running the code.
4. Truncating a verification command's output for readability (`| head -N`) is dangerous when the command's exit code and completeness both matter — this order's own mistake is now a standing cautionary case.
5. Bundling modules of different verifiability into one Manufacturing Order blurs confidence levels that should stay visible and separate.

## Required Output 2 — Manufacturing Improvements

1. Adopt a **per-module verifiability classification** (DB-dependent / external-service-dependent / self-contained) at Specification time, so a Manufacturing Order's plan makes explicit, up front, which modules can realistically be truly Runtime-Verified in the current environment and which cannot.
2. Add a **pre-flight environment-capability check** (credential presence, service reachability) as the first Assembly-phase step, not a reactive mid-order discovery.
3. Script **structural validation** and **verification-run completion checking** as named, reusable tools rather than ad hoc shell commands.
4. Revisit `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR` as the mechanism for future same-shape registry manufacturing, given this order is now a second data point that hand-writing near-identical CRUD workflow sets is the largest single time cost in a Manufacturing Order of this shape.

## Required Output 3 — Updated Manufacturing Order Template

```markdown
# MO-00X — <Product/Module Name>

Manufacturing Order: MO-00X
Product: <name>
Customer: <name, if applicable>
Version: <x.y>
Status: <DRAFT | SPECIFICATION | ASSEMBLY | RELEASE CANDIDATE | RELEASED>

## 1. Manufacturing Vehicle
Which existing product/repository location this order manufactures into, and why
(evidence that this is reuse, not a new product).

## 2. Module-by-Module Plan
| # | Module | Manufacturing Decision | Verifiability Class |
|---|---|---|---|
| | | (reuse existing / new, following <template>) | DB-dependent / external-service-dependent / self-contained |

**New-module cap:** state explicitly how many net-new modules this order manufactures,
and confirm it does not exceed the standing per-order cap (see MR-001 Recommendation).
If it would, split into MO-00X and MO-00X.Y.

## 3. Schema / Contract Design (if applicable)
Additive only — new tables/fields, nothing existing altered. Document any
intentional constraint (e.g., no cross-table FK) explicitly, with reasoning.

## 4. Reused Conventions
Name the exact existing artifact each new module is patterned after (e.g.
"follows BUILD-PACKS/BP-SEAL exactly"). A Manufacturing Order introducing a
genuinely new convention must say so explicitly and justify why no existing
one fits.

## 5. Manufacturing Process
Specification → Assembly → Verification → Testing → Release Candidate → Release,
per module, each producing a real artifact.

## 6. Pre-Flight Environment Check (new, per MR-001)
Before attempting Runtime Verification of any module: confirm required services
are reachable and required credentials are present. Record the result (present/
absent) explicitly, before Assembly begins, not discovered reactively mid-order.

## 7. Out of Scope (MMP boundary)
Stated explicitly, per module or per order.
```

## Required Output 4 — Updated Quality Gate Template

```markdown
# Quality Gate — <Module or Order Name>

## Structural Validation (always required)
- [ ] Shell syntax (`bash -n`) — 0 errors
- [ ] JSON/schema validity — 0 invalid
- [ ] Language compile check (e.g. `py_compile`) if applicable — clean
- [ ] Scope check — only intended files touched (git status diff)

## Runtime Verification (required to attempt; outcome may legitimately be BLOCKER)
- [ ] Verifiability class stated: DB-dependent / external-service-dependent / self-contained
- [ ] Pre-flight environment check performed and recorded (credential present? service reachable?)
- [ ] If self-contained or environment-capable: actually executed, real output captured, PASS/FAIL stated
- [ ] If blocked: exact blocking condition named (not vague), and confirmed external to this order's own deliverables
- [ ] If a verification runner was used: confirm its output reached its own real completion marker
  before citing any pass/fail count from it (do not truncate verification output with pipes like `head`)

## Determination
- [ ] Structural Validation: PASS / WARNING / BLOCKER
- [ ] Runtime Verification: PASS / BLOCKER (with named reason) — never omitted, never implied
- [ ] Overall module status stated independently per module, not only as one order-wide roll-up
```

## Required Output 5 — Recommended Manufacturing Workflow

```
Specification
     │  (module list, verifiability classification, reuse template named,
     │   new-module cap checked, constraints documented)
     ▼
Pre-Flight Environment Check
     │  (credentials, service reachability — recorded before Assembly)
     ▼
Assembly
     │  (per module, patterned against the named existing template;
     │   any genuinely new pattern explicitly justified)
     ▼
Structural Validation
     │  (scripted, not ad hoc: syntax, JSON validity, compile check, scope check)
     ▼
Runtime Verification
     │  (attempted for every module regardless of expected outcome;
     │   self-contained modules actually executed; DB/service-dependent
     │   modules attempted against pre-flight-checked environment;
     │   completion markers confirmed before citing results)
     ▼
Testing
     │  (per-module PASS/FAIL/BLOCKER, not just an order-wide summary)
     ▼
Release Candidate
     │  (per module AND per order — an order may be RC while individually
     │   naming which modules are fully verified vs. structurally-only)
     ▼
Release
```

## Required Output 6 — Recommendations for MO-002 Onward

1. Classify every module's verifiability at Specification time; do not discover it reactively mid-order.
2. Cap new-module count per order; split oversized orders into `MO-00X.Y` follow-ons rather than bundling categorically different modules.
3. Script structural validation and verification-run completion checking once, reuse for every future order.
4. Evaluate `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR` as the mechanism for future same-shape registry manufacturing before hand-writing another CRUD module set.
5. Continue attempting real execution wherever an environment allows it, even when other modules in the same order are blocked — this is now validated twice as the highest-value verification activity available.
6. Never pipe a verification runner's output through a line-limiting filter (`head`, `tail -n`) when its exit code or completeness will be cited — redirect to a file and read it in full instead.
