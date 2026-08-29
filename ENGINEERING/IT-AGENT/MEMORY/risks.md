# Known Risks

Standing risks worth a new investigation remembering before it starts.
Not a bug tracker — remove/update an entry once it's no longer true.

<!-- Format:
## <short title>
Risk: ...
Where it bites: ...
Noted: YYYY-MM-DD
-->

## Documentation can describe orphaned/unwired features
Risk: This repo's code comments and MWO reports are unusually detailed and
can describe a component or field as "already computed"/"already live"
when it was later orphaned by a redesign or was always a null placeholder.
Where it bites: Any "X not appearing" task — always verify actual
render/wiring (see `ai5r-observability`), never trust the comment alone.
Noted: 2026-08-29

## Production checkout can diverge from origin
Risk: The production VPS working tree has held uncommitted files and its
local HEAD has been observed to differ from `origin/release/ltsa-v1-rc1`.
Where it bites: Don't assume the deployed commit matches the latest branch
tip in GitHub, or vice versa — verify both independently before reasoning
about "what's live."
Noted: 2026-08-29

## Shared-host resource contention between DEV/test workloads and PROD
Risk: This VPS runs PROD (`ai5ros-prod`) and is also where DEV/test work
for this repo happens (dev clones, image builds). DEV Docker workloads
share the same CPU/memory/disk I/O as PROD containers even when using
different image tags, container names, and networks — that kind of
separation does not isolate the resource layer.
Factual record (2026-08-29): while building/running isolated Docker test
images for the IT Agent Foundation branch, dockerd's own journal showed
the `ai5ros-prod-api-1` container's healthcheck fail twice in escalating
fashion ("healthcheck failed" -> "healthcheck failed fatally" ->
"stopping restart-manager"/recreate), in two separate windows
(~13:04-13:05 and ~13:16-13:18 UTC), each overlapping active DEV
build/run commands on the same host. No cron job, systemd timer,
watchtower/updater container, or other operator login was found in either
window that would independently explain the recreates.
This is a strong temporal correlation, not a mathematically proven
causal link — no test isolated the DEV workload as the sole variable, and
no lower-level (cgroup/kernel) evidence was captured. It is the most
consistent explanation given everything checked, and is treated as such:
enough to change behavior (see the shared-host safety rule in
`ai5r-it-orchestrator`), not enough to state as certain fact.
Where it bites: any future DEV/test/build activity on this VPS while PROD
containers are running (docker build, docker run, npm ci, pytest, vitest,
dependency installs).
Noted: 2026-08-29
