# Architecture Decisions

Concise, dated entries only. One decision per entry: what, why, alternatives
considered in one line, link to MWO/ADR if one exists. No large design docs
here — those belong in `ADR/` or `ARCHITECTURE/ADR/`, which already exist in
this repo; this file is an index/pointer plus decisions too small for a
full ADR.

<!-- Format:
## YYYY-MM-DD — <short title>
Decision: ...
Why: ...
Alternatives: ...
Ref: MWO-... / ADR-...
-->

## 2026-08-29 — AI5R IT Agent Foundation (MWO-IT-001)
Decision: Vendor a minimal, pinned subset of ECC (github.com/affaan-m/ECC)
agents/skills as a specialist library under `.claude/`; build AI5R's own
orchestrator/observability skills natively; never install the full ECC
plugin.
Why: Need cross-stack IT specialist coverage without ceding orchestration,
token budget, or workflow control to an external, auto-updating plugin
with hooks/MCP.
Alternatives: Full `/plugin install ecc@ecc` (rejected — 354 components +
hooks, no scoping); build every specialist from scratch (rejected — no
need to reinvent well-covered patterns like FastAPI/Postgres/React
review).
Ref: ENGINEERING/IT-AGENT/README.md, ECC-ATTRIBUTION.md
