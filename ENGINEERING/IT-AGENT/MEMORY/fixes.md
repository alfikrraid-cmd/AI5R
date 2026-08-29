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
