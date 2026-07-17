# AI5R Engineering Standard
Version: 1.0
Status: ACTIVE
Authority: Chief Architect
Applies To: Every AI5R product and engineering agent (Claude or otherwise) performing implementation work inside AI5R

---

## 0. Scope Note

This standard is **not LTSA-specific**. Every rule below was extracted from what was actually practiced and proven during Sprint 01 (MWO-P-001 through MWO-P-004, executed against `PRODUCTS/LTSA-BRAIN`), but each rule is stated in product-agnostic terms so it applies to any future AI5R product. LTSA-BRAIN artifacts appear only as the supporting evidence for each rule, not as the rule's subject. No practice appears here that was not actually exercised during Sprint 01 — this document standardizes, it does not invent.

---

## 1. Purpose

This document defines the engineering standard that governs how implementation work is planned, reviewed, executed, validated, and reported within AI5R, for any product. It exists to make permanent the practices Sprint 01 proved effective, and to retire nothing that Sprint 01 proved unnecessary — Sprint 01 introduced no changes to this document; it produced the evidence this document formalizes.

**Mandatory.** Evidence: this document was directly and explicitly commissioned by Chief Architect Directive as the sprint's closing action, replacing informal, session-local convention with a durable reference.

---

## 2. Engineering Principles

- **Discipline over initiative.** No engineering session in Sprint 01 expanded scope beyond what was explicitly requested, even when related problems were discovered in passing (e.g., the unmarked `BP-PUMP` Create/Detail stubs found during Pump WP-000 were documented and left untouched, not opportunistically fixed).
- **Correctness over speed.** MWO-P-003 paused mid-implementation to correct a self-discovered SQL-parameterization defect rather than ship the faster, already-working-looking version.
- **Evidence over assumption.** Every canonicalization decision (Customer Registry, Pump Registry) was made only after directly reading every candidate artifact's actual content — not after reading a prior summary of that content.
- **Implementation follows architecture; architecture never follows implementation.** Verified independently in three consecutive MWOs (`5e349cd`, `f125dfc`, `eb9330e`) — zero new tables, services, credential mechanisms, or frameworks were introduced in any of them.
- **Engineering quality is measured by discipline, not volume.** MWO-P-004 deliberately excluded Runtime Verification and OpenAPI work from its own scope, on Chief Architect instruction, rather than completing "more" than was approved.

**Mandatory.**

---

## 3. Sprint Lifecycle

Sprint 01 followed, and this standard codifies, the following phase order for a sprint targeting an existing product with known defects:

1. **Audit phase** — one evidence-only MWO (MWO-P-001), read-only, no implementation, producing a prioritized backlog. Not committed.
2. **Recovery phase** — one MWO (MWO-P-002) resolving the audit's Critical-severity findings only, with architecture frozen and no feature work.
3. **Feature-completion phase** — one MWO per functional area (MWO-P-003 Customer Registry, MWO-P-004 Pump Registry), each gated by a mandatory canonicalization work package before any implementation.
4. **Sprint closeout phase** — a checkpoint/readiness assessment, a final engineering review, a process retrospective, and (this document) a standards update, each produced only after all sprint MWOs are committed.

**Recommended.** This exact four-phase shape is proven for a recovery-then-completion sprint; a sprint with a different starting condition (e.g., greenfield product) was not exercised in Sprint 01, so this shape is recommended as a starting template, not mandated as the only valid lifecycle.

---

## 4. MWO Lifecycle

Every Manufacturing Work Order observed in Sprint 01 passed through the same stages:

1. **Draft** — produced from prior audit/recovery evidence, never invented from scratch.
2. **Chief Architect Review** — zero to several revision rounds (MWO-P-003 took three; MWO-P-004 took one) before approval. Revisions are incorporated into the same document, not a new one.
3. **Approval** — explicit, named ("MWO-P-00X is approved") before any implementation begins.
4. **Implementation** — governed by the Work Package Lifecycle (§5).
5. **Documentation Update** — added per the Documentation Contract (§18): determine which of the eight mandatory documentation files are affected by the completed implementation, and update only those. Not optional, and not satisfied by the Completion Report alone.
6. **Completion Report** — one per MWO, produced only after every work package is individually complete and Documentation Update (stage 5) is done.
7. **Engineering Audit** — verifies, among everything else in its scope, that documentation matches actual repository state (§18). A documentation/reality mismatch is a FAIL, same severity as any other audit FAIL.
8. **Commit Recommendation** — produced only after the Engineering Audit passes; states the recommended atomic commit grouping.
9. **Commit approval** — separate, explicit, requested and granted after the Commit Recommendation, never assumed.
10. **Push approval** — separate again from commit approval; observed granted later and independently in both cases it occurred this sprint.

**Mandatory** for stages 1–3 and 5–10 (never skipped). **Recommended** for the number of revision rounds in stage 2 — Sprint 01 showed this varies by how much ambiguity the draft contains, not a fixed count. Stages 5, 7, and 8 were added by the Documentation Contract (§18); every MWO from that point forward observes the full ten-stage lifecycle.

---

## 5. Work Package Lifecycle

- **WP-000 is mandatory whenever more than one candidate implementation location exists for a module.** Both feature-completion MWOs this sprint began with a WP-000 canonicalization pass before any other work package could begin.
- Each subsequent work package follows: **implement → validate (structural) → produce a report → stop → wait for approval**, exactly as specified in each approved MWO.
- **Approval granularity must be explicitly stated in the MWO document itself.** Sprint 01 used two different granularities without ever declaring which applied: MWO-P-003 ran all seven work packages in one continuous execution with a single end-of-MWO report; MWO-P-004 required individual Chief approval after every one of its four work packages. Both produced sound results, but the choice was never stated up front in either MWO, which the Sprint 01 Retrospective identified as the sprint's clearest process inconsistency.

**Mandatory:** WP-000-first when duplication exists; the implement→validate→report→stop→wait sequence. **Recommended:** declaring approval granularity explicitly in the MWO document before implementation begins (not exercised this sprint, but directly derived from a Sprint 01 finding).

---

## 6. Canonicalization Standard

Proven twice, on two structurally different duplication patterns (Customer Registry's two-location split; Pump Registry's three-location split with an additional schema-level mismatch discovered only by reading embedded workflow metadata directly).

A canonicalization work package must:
1. Identify every artifact for the module in question, by direct read, not by citation of a prior report.
2. Compare candidate implementations against whichever is closest to the product's own already-documented or already-functioning contract (evidenced, not assumed).
3. Produce a Canonical Mapping Table: one row per operation/unit, with Canonical and Deprecated columns.
4. **Lock the mapping.** No canonical decision may change during subsequent implementation. If implementation surfaces evidence contradicting a locked mapping, implementation must stop, the evidence must be documented, and a new work order must be proposed — not decided in place.
5. Deprecated artifacts are marked, never deleted, using a convention appropriate to the file type (a leading comment header for formats that support comments; additive, ignored metadata fields for formats that do not, such as JSON).

**Mandatory**, in full — every element above was both specified and actually exercised (the lock rule was written into MWO-P-004 before implementation and never needed to be invoked, but its presence was treated as non-negotiable).

---

## 7. Evidence Standard

- **No canonicalization, validation, or completion claim may be made without direct evidence.** Reading a prior report's summary of a file is not equivalent to reading the file.
- **Corrections to prior findings must be recorded, not silently overwritten.** MWO-P-002 corrected an MWO-P-001 finding (a workflow file believed missing was found to exist) by quoting the original claim, stating what the new evidence showed, and marking the original document unmodified — the historical record was preserved even while being corrected.
- **Every engineering report must cite specific file paths**, and where relevant, specific fields or line content, rather than general claims of correctness.
- **A finding that later proves wrong must be disclosed as a finding that proved wrong**, not quietly dropped. This applies equally to a prior MWO's own audit and to a work package's own first draft (MWO-P-003's self-caught parameterization defect).

**Mandatory.**

---

## 8. Validation Standard

Two categories, kept explicitly separate — a Sprint 01 refinement (introduced in MWO-P-004's revision) that measurably improved report clarity over the earlier, undifferentiated approach used in MWO-P-002/P-003:

**Structural Validation** (always in scope for implementation work):
- Syntax/format validation of every created or modified artifact.
- Node/dependency graph completeness — every element reachable, every execution path terminating correctly.
- Canonical validation — confirmation that implementation targeted exactly the file the locked canonical map designates, and no other.
- Static schema/field review — manual cross-check of any field, column, or parameter list against the actual canonical definition.
- Scope validation — confirmation, via direct tooling (e.g., version-control status), that only the intended files were touched.

**Runtime Verification** (a distinct category — live execution, live data-store verification, response verification, integration verification):
- Must never be implied by a Structural Validation PASS.
- If not performed, this must be stated explicitly, along with the specific reason (Sprint 01's recurring reason: no reachable, credentialed execution environment was available in-session).
- A written-but-unexecuted test or workflow must be reported as such — never represented as verified.

**Mandatory**, in full. This is the direct, structural answer to the failure mode MWO-P-001 originally found (a report claiming production verification that had not occurred) and every subsequent MWO this sprint was built not to repeat it.

---

## 9. Review Standard

- Implementation may not begin without explicit Chief Architect approval of the governing work order.
- Canonicalization decisions (WP-000) require their own explicit approval, separate from approval of the implementation work packages that depend on them.
- Reviews may request revisions to a draft work order before approving it; revisions are incorporated in place, and the document's own status line should reflect its current state (draft, revised, approved, in-progress, complete) so its state is legible without cross-referencing chat history.

**Mandatory.**

---

## 10. Commit Standard

- **One MWO, one commit.** Observed and held exactly three times this sprint (`5e349cd`, `f125dfc`, `eb9330e`), each corresponding to exactly one completed, approved MWO.
- **Never stage by wildcard.** Every commit this sprint staged files individually, by explicit path, verified against a fresh status check immediately before staging — this is how, each time, files unrelated to the MWO (a pending governance draft, an uncommitted audit document, an unrelated package) were correctly excluded.
- **Commit requires its own explicit approval**, separate from approval of the implementation itself.
- **Commit message states the MWO identifier and a one-line summary of what was completed**, following the pattern `MWO-P-00X: <summary>`, with co-authorship attribution where applicable.

**Mandatory.**

---

## 11. Push Standard

- **Push is a separate, later approval from commit — never bundled automatically.** Demonstrated twice: once after MWO-P-003's commit (approved and pushed together with the already-committed MWO-P-002), and once after MWO-P-004's commit (committed on explicit instruction to stop and wait, pushed only on a distinct, later, explicit instruction).
- Push should be preceded by a status check confirming exactly the expected commit(s) are ahead of the remote, and followed by displaying the result (log, status, branch tracking) so the outcome is independently verifiable, not just asserted.

**Mandatory.**

---

## 12. Engineering Reports

Sprint 01 produced four categories of report, each proven and each with a distinct purpose:

1. **Per-work-package reports**, one per WP, prefixed by a short context-specific code (`IR` for the integrity recovery MWO, `CR` for Customer Registry, `PM` for Pump Module). **The prefix `PR` must never be used** — it collides with Pull Request terminology, a collision Sprint 01 identified and corrected mid-sprint. Each report should contain, at minimum: Objective, Implementation summary, Structural Validation results, a single explicit PASS/WARNING/BLOCKER determination, Known Limitations, and — where the work package draws on prior evidence or an established pattern — an explicit Evidence Used and/or Pattern Source section.
2. **MWO-level summary/completion reports**, produced once per MWO after all its work packages are individually complete, aggregating (not re-deriving) their results.
3. **Sprint-level reports** — a mid-sprint checkpoint, an end-of-sprint engineering review, and a process retrospective. Sprint 01 produced these as three separate documents with material content overlap (see §17).
4. **This document** — a standards artifact, produced once at sprint close, distinct from all of the above.

**Mandatory:** the per-work-package report, the PASS/WARNING/BLOCKER determination, and the `PR`-avoidance naming rule. **Recommended:** the specific section list above, as a minimum, not a ceiling.

---

## 13. Execution Modes

Sprint 01 operated in three distinct, explicitly-signaled modes, and every instruction this sprint stated which mode applied:

- **Analysis Mode** — read repository state, produce a report or document as a response; no repository file is created or modified. Used for the audit, the sprint checkpoint, the engineering review, and the retrospective.
- **Document Drafting Mode** — produce an engineering document (an MWO, a standards document) and save it to the repository as a file; no product code is touched, no commit or push occurs without separate approval.
- **Implementation Mode** — governed entirely by an approved MWO and its Work Package Lifecycle (§5); the only mode in which product code or product data-schema files may be created or modified.

**Mandatory.** Every instruction that initiated work this sprint specified which of these three applied, and no work was ever performed under an unstated or ambiguous mode.

---

## 14. Definition of Done

**For a Work Package:**
- Its canonical file exists, is structurally valid, and was built at exactly the location the locked canonical map designates.
- Any corresponding deprecated file is marked, not deleted.
- The canonical mapping is unchanged from what WP-000 locked.
- Structural Validation is complete and its result stated as PASS, WARNING, or BLOCKER — never omitted or implied.
- A report exists for the work package.

**For an MWO** (extended by the Documentation Contract, §18):
- Every work package in its approved scope is individually complete per the above.
- No file outside its approved scope was touched (verified, not assumed).
- The canonical mapping remained unchanged throughout implementation.
- Runtime verification is complete, or its absence is stated explicitly with a specific reason (§8) — never omitted.
- Documentation is updated — only the files the completed MWO's own scope affects, per the Documentation Contract (§18); never skipped, never satisfied by the Completion Report alone.
- A completion report exists, aggregating all work package results.
- An Engineering Audit has passed, including its documentation-consistency check (§18).
- A Commit Recommendation has been produced.
- Nothing is committed or pushed without separate, explicit approval for each.

Only once every item above is met may the MWO be considered **Commit Ready**.

**Mandatory** — the first four items are drawn directly from the Definition of Done sections written into MWO-P-003 and MWO-P-004 themselves, verified item by item against actual outcomes at each MWO's completion. The Documentation Update, Engineering Audit, and Commit Recommendation items were added by the Documentation Contract (§18) and apply to every MWO from that point forward.

---

## 15. Engineering Vocabulary

Terms proven and used consistently across Sprint 01; future work should reuse them rather than introduce synonyms:

- **MWO (Manufacturing Work Order)** — the unit of approved implementation scope.
- **WP (Work Package)** — one unit of implementation within an MWO; WP-000 is reserved for canonicalization.
- **Canonical / Deprecated** — exactly one artifact per operation is canonical; any duplicate is deprecated, marked, and retained.
- **Structural Validation** — verification of an artifact's internal correctness and consistency without executing it.
- **Runtime Verification** — verification of an artifact's actual behavior via live execution; a distinct category from Structural Validation, never implied by it.
- **PASS / WARNING / BLOCKER** — the three permitted outcome states for any validation; WARNING marks a known, disclosed limitation (not a hidden defect); BLOCKER marks a finding that prevents proceeding.
- **Chief Architect** — owns vision, architecture, priority, scope, and all commit/push/release approval.
- **Implementation Engineer** — owns repository analysis, evidence collection, implementation, validation, and technical reporting; does not redefine priority or scope.

**Mandatory.**

---

## 16. Lessons Learned

Carried forward verbatim in substance from the Sprint 01 Retrospective, as the standard's own justification for several rules above:

- Process discipline is not a substitute for Runtime Verification, and the two must never be conflated in a report (§8).
- Audit and recovery findings are provisional evidence, not final truth, and must be revisited when new evidence contradicts them (§7).
- A validated implementation pattern transfers across modules efficiently only when adaptations are evidence-driven, not copied blindly (§6, §7).
- Separating validation into explicit phases prevents an implicit, unearned claim of correctness from ever appearing in a report, especially as scope grows across multiple modules (§8).

**Mandatory** — these are the direct rationale for §6–§8 above, not separate optional guidance.

---

## 17. Sprint 02 Process Changes

Carried forward from the Sprint 01 Retrospective as the specific, evidence-based process adjustments to apply going forward:

1. **State approval granularity explicitly in every MWO document** before implementation begins (§5) — Sprint 01 used two different granularities without ever declaring either as the chosen one.
2. **Consolidate sprint-boundary reporting.** Sprint 01 produced a checkpoint report, a per-MWO completion report, an engineering review, and a retrospective in close succession, with material overlap between them (Production Readiness and Remaining Risks were each independently re-derived more than once). Sprint 02 should have later sprint-level reports incorporate earlier ones by reference rather than recomputing overlapping content from scratch.
3. **Limit drift-verification checks to once per MWO** (before its first work package, and once more before its completion report), rather than before every individual work package, absent a specific reason to suspect concurrent change.
4. **Treat Runtime Verification infrastructure as the first standing question for Sprint 02's planning** — every synthesis report produced in Sprint 01 independently arrived at this as the top unresolved item; it should not need to be rediscovered a fifth time.

**Recommended** — these are process adjustments proposed on the strength of Sprint 01 evidence, not yet themselves tested in practice. They should be treated as the working default for Sprint 02 and revisited in that sprint's own retrospective.

---

## 18. Documentation Contract

Established per Chief Architect directive, following the Engineering Knowledge Acquisition epic (MWO-LTSA-030/040A–040E) and its Engineering Audit (`EA-001`)/RCA (`RCA-001`). Full policy text: `DOCUMENTATION_CONTRACT.md` at the project root — this section incorporates it by reference and states its effect on this Standard; it is not duplicated here.

**Golden Rule:** documentation is part of the implementation. Implementation is not complete until project documentation has been updated. A Completion Report alone is not sufficient — the Engineering Audit must verify documentation consistency before Commit.

**Mandatory Documentation** — eight files at the project root, reused if present, created only if missing, never duplicated elsewhere: `CLAUDE.md`, `CURRENT_STATE.md`, `CHANGELOG.md`, `PROJECT_HISTORY.md`, `ROADMAP.md`, `MEMORY.md`, `TECHNICAL_DEBT.md`, `DOCUMENTATION_CONTRACT.md`. Each file's purpose and update cadence is defined in `DOCUMENTATION_CONTRACT.md`'s own table, not restated here.

**Effect on the MWO Lifecycle (§4):** Documentation Update, Engineering Audit, and Commit Recommendation are now explicit, mandatory stages between Implementation and Commit approval — not implied by, and not satisfied by, the Completion Report alone.

**Effect on Definition of Done (§14):** an MWO's "for an MWO" checklist now includes Documentation Update, Engineering Audit passed, and Commit Recommendation produced, alongside the pre-existing criteria. An MWO is **Commit Ready** only once every criterion in §14 is met.

**Effect on Engineering Audit:** documentation-consistency verification (does documentation match actual repository state — schema, build packs, ADRs) is now one of the Engineering Audit's checks, alongside file grouping, duplicate detection, architecture compliance, BUILD-PACK consistency, and the Runtime/Registry/Product boundary. A documentation/reality mismatch is reported as **FAIL**, the same severity as any other audit FAIL, and the audit stops there rather than proceeding to a commit recommendation.

**Documentation Update Rule:** whenever an MWO is completed, the affected documentation files are determined automatically from the MWO's own scope and deliverables — never by asking the user which files apply. Only affected files are updated; unaffected files are left unchanged, never rewritten wholesale.

**Mandatory**, in full, for every MWO from the point this section was added onward.

---

Established per Chief Architect Directive at the close of Sprint 01, extended by Chief Architect directive to add the Documentation Contract (§18). This document was created/extended only; nothing was implemented, no MWO was drafted, no commit was made, and nothing was pushed in producing either version.
