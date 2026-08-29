# Incidents

One entry per investigated "IT:" symptom. Root cause only, no raw logs.

<!-- Format:
## YYYY-MM-DD — <symptom, one line>
Module: ...
Root cause: ...
Evidence: <file:line / command, not a log dump>
Status: open / fixed (MWO-...) / diagnosis-only, no code change needed
-->

## 2026-08-29 — Fleet MTBF/MTTR tiles missing from Executive Dashboard (mock IT task, diagnosis only)
Module: LTSA / AI5R-STUDIO/dashboard (Executive Dashboard)
Root cause: FleetMetricsGrid (the live MTBF/MTTR display) renders only when
BOTH getFleetReliability() AND getFleetPowerBI() resolve
(reliability && summary gate in ExecutiveDashboard.jsx line 178) - a
Power BI-only failure hides the reliability tiles with no visible error.
FleetReliabilityPanel.jsx (a standalone reliability card) is fully built
and tested but not imported by any page (orphaned since the MWO-LTSA-040A
redesign) - not the cause of this symptom, but a related dead component.
Evidence: AI5R-STUDIO/dashboard/src/modules/ltsa/pages/ExecutiveDashboard.jsx:178
(re-verified current on 2026-08-29; no import of FleetReliabilityPanel
found anywhere outside comments/tests).
Status: diagnosis-only, no code change made (mock IT task) - a real fix
(decouple the two optional fetches render gates) would warrant its own
MWO; not opened, see unresolved-tasks.md.

## 2026-08-29 — DEV Docker test activity correlated with two PROD api healthcheck failures/recreates
Module: Infrastructure (shared VPS, `ai5ros-prod` compose project)
Root cause: not proven with certainty. Strongest available explanation:
CPU/IO contention from DEV Docker image builds/container runs (for this
branch's isolated backend/frontend test setup) on the same host as PROD,
coinciding with `ai5ros-prod-api-1` healthcheck failures that led Docker
to recreate the container — twice, in two separate ~1-2 minute windows.
Evidence: dockerd journal showed the same escalation pattern both times
("healthcheck failed" -> "healthcheck failed fatally" -> "stopping
restart-manager"), each window overlapping active DEV build/run commands;
container Created/StartedAt timestamps confirm fresh recreates (not
crash-restarts — RestartCount reset to 0, clean ExitCode 0 each time). No
cron, systemd timer, watchtower, or other-operator login found that would
independently explain either recreate.
Status: fixed (policy, not code) — see `risks.md` and the "Shared-host
safety" section added to `ai5r-it-orchestrator/SKILL.md`: resource-
intensive DEV/test/build operations now require either genuinely separate
infrastructure or explicit maintenance-window approval before running on
a host that also serves PROD. No PROD file/container/DB/n8n config was
directly touched at any point; the impact was resource contention only,
and PROD returned to stable/healthy within minutes once the DEV workload
stopped.
