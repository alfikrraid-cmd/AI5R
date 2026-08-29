# Unresolved Tasks

Open threads the IT agent surfaced but did not resolve — needs a human
decision, more evidence, or is out of this layer's authorized scope
(e.g. anything hitting the hard-safety boundaries).

<!-- Format:
## YYYY-MM-DD — <short title>
What's blocking: ...
Needed: ...
-->

## 2026-08-29 — Decouple Fleet Reliability tiles from Power BI fetch gate
What's blocking: Needs an MWO + human product decision (should the two
optional fetches render independently, and should a failure surface any
visible state instead of silently omitting the section?) before any code
change — out of scope for a diagnosis-only mock task.
Needed: Product owner sign-off on desired behavior, then a small MWO.

## 2026-08-29 — Ready-to-review fix branch: fix/historical-ingestion-pdfplumber-dependency
What's blocking: Human review and merge decision (not an IT Agent
limitation -- merging to release is explicitly outside this agent's
authority). The branch is pushed, CI-verified green (see
MEMORY/fixes.md), and branched cleanly from release/ltsa-v1-rc1.
Needed: A maintainer to review and merge
fix/historical-ingestion-pdfplumber-dependency into release/ltsa-v1-rc1.

## Structural note: IT Agent memory system not yet on release/ltsa-v1-rc1
What's blocking: ENGINEERING/IT-AGENT/MEMORY/ only exists on
feature/ai5r-it-agent-foundation today, so real product fixes (which
correctly branch from release/ltsa-v1-rc1, not from this foundation
branch) can't record their own memory entry in place -- they get
recorded here instead, cross-referencing the fix branch/commit.
Needed: Once feature/ai5r-it-agent-foundation is reviewed and merged to
release, this stops being necessary -- memory entries can then live
alongside the code they describe.
