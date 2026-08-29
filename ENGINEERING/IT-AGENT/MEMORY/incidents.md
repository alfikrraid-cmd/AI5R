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
