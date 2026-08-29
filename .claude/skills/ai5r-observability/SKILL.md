---
name: ai5r-observability
description: Read-only runtime observability for AI5R's deployed stack (docker compose services, container health/logs, n8n workflow execution history). Use when an IT task needs to know what is actually running/healthy right now, or what a service actually logged, rather than what the code says should happen. No ECC equivalent exists for this role; authored for AI5R directly.
metadata:
  origin: AI5R
---

# AI5R Observability

Fills a real gap: ECC's vendored library has no infrastructure-observability
component. This skill is intentionally thin and always read-only — it wraps
commands already used safely during prior read-only audits of this stack,
it does not introduce a new monitoring system, dependency, or dashboard.

## Scope

Runtime evidence only. This skill never proposes or runs a mutating
command (no restart, no recreate, no scale, no rm, no exec that writes).
If a finding suggests a restart/redeploy is needed, say so in the report
and stop — that action requires explicit human approval outside this
skill, same as every other hard-safety boundary in
`ai5r-it-orchestrator`.

## Checks

Container / service health (compose project `ai5ros-prod`, runtime at
`CORE-SERVICES/RUNTIME/compose.yaml`):

```bash
docker compose -p ai5ros-prod -f CORE-SERVICES/RUNTIME/compose.yaml ps
docker compose -p ai5ros-prod -f CORE-SERVICES/RUNTIME/compose.yaml logs --tail=200 <service>
```

Known services: api, dashboard, gotenberg, minio, n8n, neo4j, nginx,
postgres, redis. Use `ps` first to see current status/health before
pulling logs — don't dump logs for a healthy, unrelated service.

n8n workflow execution history (relevant whenever a backend gateway proxies
through an n8n webhook — most AI5R gateways do, e.g. `cm_report_gateway.py`
-> `http://localhost:5678/webhook/ltsa/cm-report/...`): check the n8n UI's
execution list for the specific workflow, or the n8n container's own logs,
for failed/errored executions around the reported time window. This is
usually the fastest way to confirm whether "data not appearing" is a
gateway-reachability problem vs. a frontend-wiring problem vs. a real
upstream-data gap.

Application-level evidence: prefer an existing health/status endpoint
(e.g. `routers/health.py`) over inferring health from container `Up`
status alone — a container can be `Up (healthy)` on its Docker healthcheck
while the application layer it serves is still failing a specific request
path.

## Output

Report exactly what was observed (status strings, log lines, timestamps),
never an inference dressed as a fact. If nothing abnormal was found, say
so plainly — do not manufacture a finding to justify having run the check.
Never paste full/large log dumps into IT memory (see
`ENGINEERING/IT-AGENT/MEMORY/`) — summarize the 1-3 lines that matter.

## Anti-pattern this skill exists to prevent

Trusting a code comment or MWO report's claim that something "is live" or
"already computed" without confirming the process that would make it true
is actually running and reachable. This repo's own history has at least
one confirmed case of a documented, tested UI panel that was fully built
but never wired into any page (orphaned after a later redesign) — a
runtime/wiring check would have caught that in seconds; reading the
component's own code and comments alone would not.
