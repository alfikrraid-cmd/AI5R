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

## 2026-08-30 — Human decision needed: ship or hold fix/ltsa-messaging-gateway-implementation
What's blocking: python-reviewer specialist Block verdict on
get_fleet_summary()'s missing area/MA scope enforcement (see risks.md).
The fix itself correctly and completely resolves the assigned issue
(CORE-SERVICES/API/TESTS collection failure) and matches the pre-existing
test's own contract exactly -- the scope gap is inherited from that
contract, not introduced here, and the module has zero live blast radius
today (nothing imports it yet).
Needed: A maintainer decision -- (a) merge as-is and open a dedicated
follow-up MWO for scope-closure before this gateway is ever wired to a
real router/channel (mirrors this repo's own precedent), or (b) hold the
merge until scope-threading is added now. Either way, review
fix/ltsa-messaging-gateway-implementation (CI-verified green for its own
tests) before deciding.
Decision as of 2026-08-30 (AI5R IT Agent Foundation v1 release): HOLD.
Not merged into release/ltsa-v1-rc1 at 40a38bf. Status =
HOLD_SECURITY_SCOPE_CLOSURE -- remains blocked pending a dedicated MWO to
close the area/MA scope-enforcement gap before this gateway is shipped or
wired to any router/channel.

## 2026-08-30 — Investigate test_auth_admin_service.py DelegationDeniedError failure
What's blocking: Needs its own investigation -- out of MWO-LTSA-039A's
scope, discovered only as a side effect of CORE-SERVICES/API/TESTS
finally being able to complete collection. Possibly security-relevant
(a TAP_ADMIN delegation restriction not being enforced) or possibly a
stale test assertion -- not determined here.
Needed: A separate IT: task to classify and, if it's a real gap, fix.
