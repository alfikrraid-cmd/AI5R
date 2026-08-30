# Deployment History

High-level only — what shipped, when, which MWO. Not a replacement for
`docker compose` state or git history; a fast index over both.

<!-- Format:
## YYYY-MM-DD — <what>
MWO: MWO-...
Verified via: `docker compose ps` / health endpoint / manual check
-->

## 2026-08-30 — AI5R IT Agent Foundation v1 merged to release; production checkout fast-forwarded
MWO: MWO-IT-001, MWO-LTSA-HISTORICAL-INGESTION-DEPENDENCY-001
What shipped: AI5R IT Agent Foundation v1 (feature/ai5r-it-agent-foundation)
and the MWO-LTSA-HISTORICAL-INGESTION-DEPENDENCY-001 acceptance-#1 minimal
fix merged into `release/ltsa-v1-rc1` at 40a38bf23b998dc17be7ef09706b0b359152e446.
Post-merge CI verified zero new regressions; the merge resolved 5
pre-existing pdfplumber-related baseline failures (see fixes.md,
2026-08-29 entry).
Production action: `/home/unikom666/AI5R-PROD` checkout advanced from
1b5fd92fb96f6ac5bd8bf2df34fc41dc394c96a1 to 40a38bf via `git merge
--ff-only` only — no rebase, no reset, no force-checkout.
Runtime impact: zero. Docker build=0, container restart/recreate=0, DB
mutation=0, n8n mutation=0, env/secret mutation=0, downtime=0. The
running API image was intentionally NOT rebuilt: `pdfplumber` now exists
in CORE-SERVICES/BACKEND-API/requirements.txt but is not yet installed in
the unchanged, already-running API container. The historical PM/CM
ingestion CLI (the only consumer of pdfplumber) is not a live runtime
path today — it is not imported by the running FastAPI app, not
scheduled, and not wired to n8n.
Not released: the Messaging Gateway implementation
(fix/ltsa-messaging-gateway-implementation) was NOT part of this merge —
see unresolved-tasks.md (HOLD_SECURITY_SCOPE_CLOSURE).
Verified via: pre/post container-ID and image-ID diff (identical for all
9 containers), `/health` (200, database OK, n8n OK), `/healthz` (200),
dashboard HTTP (200).
