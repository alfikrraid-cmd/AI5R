# Fixes

One entry per code change made through the IT agent workflow. If it's a
real product fix it also has an MWO under `ENGINEERING/MWO/` — link it
here rather than duplicating the description.

<!-- Format:
## YYYY-MM-DD — <short title>
MWO: MWO-...
Change: <one line, what/where>
Tests: <what was added/updated>
Verified: <runtime check performed>
-->

## 2026-08-29 — Historical PM/CM ingestion fails in a clean environment (MWO-LTSA-HISTORICAL-INGESTION-DEPENDENCY-001)
MWO: MWO-LTSA-HISTORICAL-INGESTION-DEPENDENCY-001 (real product fix,
first end-to-end IT Agent acceptance test)
Change: Added `pdfplumber` to CORE-SERVICES/BACKEND-API/requirements.txt.
Root cause: historical_pm_cmon_cli.py (the real ingestion CLI entry
point) transitively imports pdfplumber via historical_pm_cmon_orchestrator.py
-> historical_pm_cmon_extraction.py, but pdfplumber was never declared in
requirements.txt (the exact file api.Dockerfile installs from), so the
CLI crashed at import time in any clean environment. Confirmed the live
FastAPI app itself never imports this chain, so production was never
affected.
Tests: new CORE-SERVICES/BACKEND-API/TESTS/test_historical_ingestion_dependency_closure.py
(TDD: committed red first, verified failing with the exact
ModuleNotFoundError via GitHub Actions CI, then committed the fix and
verified green in a second CI run). Side effect confirmed via the same
CI run: 5 pre-existing baseline failures in
test_historical_incomplete_data_policy.py::TestStagingBridgePumpTagRule
(same root cause) resolved as well. The 45 unrelated Class C
real-stack-integration baseline failures were unaffected, as expected.
Verified: Two GitHub Actions runs (red then green) on a dedicated branch,
`fix/historical-ingestion-pdfplumber-dependency`, branched from
origin/release/ltsa-v1-rc1. Not merged to release -- left for human
review/merge, per IT Agent hard-safety (no merge to release, no deploy).
Note: this MWO's own memory entry lives here (feature/ai5r-it-agent-foundation)
rather than on the fix branch, since the IT Agent's memory system is not
yet merged into release/ltsa-v1-rc1 -- see ENGINEERING/IT-AGENT/MEMORY/unresolved-tasks.md.

## 2026-08-30 — CORE-SERVICES/API test suite cannot complete collection (MWO-LTSA-039A, second acceptance test)
MWO: MWO-LTSA-039A (pre-existing, referenced by test_ltsa_messaging_gateway.py
since commit c5078a0; never previously completed -- no completion report
existed under ENGINEERING/MWO/ before this fix)
Change: Added CORE-SERVICES/API/ltsa_messaging_gateway.py (LTSAMessagingGateway,
MessageRequest, MessageResponse), implementing exactly the contract the
pre-existing test file already specified.
Root cause (git-history-verified, not assumed): the test file was
committed alongside 3 siblings (executive_metrics, pump_lifecycle,
recommendation_engine) as "completed work that had never been committed"
-- 3 of 4 implementations exist in the repo; only this one was never
written. `git log --all` confirms ltsa_messaging_gateway.py has never
existed at any point in this repository's history -- not a rename, not
a deletion, not a wrong import path.
Tests: red (collection aborted, "Interrupted: 1 error during collection",
exit code 2) -> green (collection succeeds, all ~19
test_ltsa_messaging_gateway.py tests pass, exit code changes to 1 only
because of pre-existing unrelated failures below). Verified via 2 GitHub
Actions runs on fix/ltsa-messaging-gateway-implementation.
First-ever completed run of this suite also surfaced 24 pre-existing
issues invisible until now: 23 known Class C real-stack tests
(test_import_cli.py, same docker-compose-exec-psql pattern already
documented) + 1 unrelated auth test failure -- see risks.md.
BLOCKER before merge: python-reviewer specialist dispatch returned a
Block verdict -- get_fleet_summary() has no area/MA scope enforcement,
matching a class of leak already fixed once elsewhere
(MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001). Confirmed this gap is
inherited from the pre-existing test's own Fake contract (takes no scope
argument), not introduced by this fix -- adding scope threading now
would mean inventing behavior beyond current test evidence. Recorded as
a MUST-fix-before-wiring risk, not fixed in this MWO. Human decision
needed: ship as-is (resolves the assigned collection-blocking issue,
matches existing test contract, zero live blast radius since nothing
imports this module yet) vs. hold for a dedicated scope-closure MWO
first.
Verified: fix/ltsa-messaging-gateway-implementation, branched from
release/ltsa-v1-rc1. Not merged -- left for human review per hard safety
and the scope decision above.
