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

## CORE-SERVICES/API/TESTS entire suite blocked at collection (pre-existing)
Risk: The whole suite (not an individual test) fails to collect at all.
`CORE-SERVICES/API/TESTS/test_ltsa_messaging_gateway.py` does
`from API.ltsa_messaging_gateway import LTSAMessagingGateway, MessageRequest,
MessageResponse`, but `CORE-SERVICES/API/ltsa_messaging_gateway.py` does not
exist anywhere in the repository (confirmed by a repo-wide filename
search). pytest aborts the entire collection run on this single import
error ("Interrupted: 1 error during collection"), so none of this
suite's other tests produce a result in CI, regardless of PYTHONPATH.
Where it bites: any CI job or local run that tries `pytest
CORE-SERVICES/API/TESTS` will report 0 useful results until this
pre-existing gap (a missing/orphaned module the test file still
references) is resolved. Confirmed via the first real GitHub Actions
execution of this suite (2026-08-29, workflow run 33261503281) -- not
caused by, and not fixed by, the IT Agent Foundation branch.
Noted: 2026-08-29

## LTSAMessagingGateway.get_fleet_summary() has no area/MA scope enforcement (CRITICAL, pre-wiring)
Risk: `CORE-SERVICES/API/ltsa_messaging_gateway.py` (added for
MWO-LTSA-039A, see fixes.md) calls
`fleet_executive_summary_service.build()` with no `scope` argument,
which defaults to unrestricted (every pump, every area) per
FleetExecutiveSummaryService's own contract. This exactly reopens the
class of leak MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 already fixed
for /api/ltsa/fleet/powerbi (which always threads
scope=resolve_area_scope(current_user)). MessageRequest/get_fleet_summary
currently carry no identity/scope concept at all.
Why not fixed now: the pre-existing test file
(test_ltsa_messaging_gateway.py, part of MWO-LTSA-039A) specifies this
exact no-scope-argument contract via its own
FakeFleetExecutiveSummaryService.build(self) fixture -- adding scope
threading would mean inventing new test cases/API shape beyond what any
existing evidence specifies, not implementing an already-specified
contract. This mirrors this codebase's own established two-phase
pattern (FleetReliabilityService/get_fleet_powerbi were also built
unscoped first, then scope-closed in a dedicated follow-up MWO) --
appropriate to repeat here as its own MWO, not to invent unilaterally.
Where it bites: the moment anyone wires this gateway to a real channel/
router (WhatsApp, an HTTP endpoint, anything), any area-restricted
(Pertamina) user's fleet summary request would return fleet-wide data
in violation of the same policy MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001
established. Currently zero live blast radius: this module is not
imported by main.py/dependencies.py or any router today (confirmed --
and its own test file's structural guards explicitly forbid a router/
FastAPI import at this stage).
MUST be resolved (a dedicated scope-closure MWO, mirroring
MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001) BEFORE this gateway is ever
wired to any real request path.
Noted: 2026-08-30 (surfaced by python-reviewer specialist dispatch during
MWO-LTSA-039A's own acceptance-test fix, Block verdict)

## test_auth_admin_service.py::TestAuthorizeUserManagement::test_tap_admin_cannot_manage_john_crane_engineer fails (newly surfaced, unrelated)
Risk: "DID NOT RAISE DelegationDeniedError" -- a TAP_ADMIN role test
expects a delegation-management restriction to be enforced and it isn't,
per this one test. Surfaced for the first time in this repo's CI history
on 2026-08-30 (CORE-SERVICES/API/TESTS could never complete collection
before this session's MWO-LTSA-039A fix, so this pre-existing failure
was always there but invisible). Completely unrelated to
LTSAMessagingGateway or the collection-blocking bug. Not investigated
further here -- out of MWO-LTSA-039A's scope, and NOT a "known,
already-understood" issue like the Class C real-stack tests are. Needs
its own separate IT ticket/MWO to investigate whether this is a genuine
authorization gap (given the DelegationDeniedError name, this may be
security-relevant) or a stale test assertion.
Noted: 2026-08-30
