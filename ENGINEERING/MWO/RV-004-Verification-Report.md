# RV-004 — Verification Report

Parent: MWO-P-006 — Runtime Verification Infrastructure (WP-004)
Branch: `feature/ltsa-brain` (local; not committed)

**Precise scope statement, per Chief Architect instruction: this report does not claim Runtime Verification succeeded, and does not claim full Runtime Verification was ever in this MWO's scope.** No n8n instance is reachable from this environment (unchanged since `MWO-P-001` §5/§9). What was attempted below is database-level execution of each workflow's embedded SQL against a real PostgreSQL server — the scope this MWO's Executive Summary and WP-000 defined from the outset. The result is: **the infrastructure works; the verification itself did not complete, for one specific, named reason.**

---

## What Was Attempted

`VERIFICATION/run_verification.sh` was executed for real, twice, against this environment as found — no credential was fabricated, guessed, or searched for.

**First attempt** (before a defect fix described below): hung indefinitely. Confirmed via `tasklist`: multiple `psql.exe` processes remained alive, blocked on an interactive password prompt. Manually terminated via `taskkill`.

**Root cause found:** `psql_common.sh`'s first draft (WP-001) omitted the `-w` flag. Without it, `psql` falls back to an interactive password prompt when no credential is supplied, instead of failing immediately — and that prompt can never be answered in a non-interactive session, so the process hangs forever rather than erroring. This defect was also present, unmodified, in the original inline pattern this file was extracted from (`BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/TEST/customer_*_test.sh`, from MWO-P-003) and remains present there, since those files are out of this MWO's scope to modify.

**Fix applied:** `psql_common.sh` now passes `-w` to every `psql` invocation (fails fast on a missing credential instead of hanging) — a correction to this MWO's own new file, not a modification to Customer Registry. `run_verification.sh` was additionally hardened with a 60-second `timeout` wrapper around every invocation, so the runner itself cannot hang indefinitely regardless of what a discovered script does — this protects against the same defect class in Customer Registry's still-unmodified scripts, without touching them.

**Second attempt** (after the fix): completed cleanly, start to finish, in well under the runner's overall time budget. No process required manual termination. Confirmed via `tasklist` immediately after: zero `psql.exe` processes remaining.

---

## Actual Results, Per Script

| Script | Outcome | Detail |
|---|---|---|
| `customer_by_code_test.sh` | FAIL (timeout, 60s) | Original inline pattern lacks `-w`; blocked on interactive password prompt, killed by the runner's timeout. |
| `customer_create_test.sh` | FAIL (timeout, 60s) | Same cause. |
| `customer_delete_test.sh` | FAIL (timeout, 60s) | Same cause. |
| `customer_detail_test.sh` | FAIL (timeout, 60s) | Same cause. |
| `customer_list_test.sh` | FAIL (timeout, 60s) | Same cause. |
| `customer_registry_test.sh` | **SKIPPED** | Correctly identified as `DEPRECATED` (per its MWO-P-003 comment header) and not run — the intended behavior, not a failure. |
| `customer_update_test.sh` | FAIL (timeout, 60s) | Same cause. |
| `pump_create_test.sh` | FAIL (fast, ~1s) | `psql: error: connection to server at "localhost" (::1), port 5432 failed: fe_sendauth: no password supplied` |
| `pump_detail_test.sh` | FAIL (fast, ~1s) | Same error. |
| `pump_list_test.sh` | FAIL (fast, ~1s) | Same error. |
| `pump_update_test.sh` | FAIL (fast, ~1s) | Same error. |
| `pump_delete_test.sh` | FAIL (fast, ~1s) | Same error. |
| `seal_create_test.sh` | FAIL (fast, ~1s) | Same error. |
| `seal_detail_test.sh` | FAIL (fast, ~1s) | Same error. |
| `seal_list_test.sh` | FAIL (fast, ~1s) | Same error. |
| `seal_update_test.sh` | FAIL (fast, ~1s) | Same error. |
| `seal_delete_test.sh` | FAIL (fast, ~1s) | Same error. |

**Summary: 17 discovered, 1 correctly skipped, 0 passed, 16 failed.** Every failure traces to the identical root cause: **no usable PostgreSQL connection is available in this session.** `LTSA_TEST_DSN` is unset; no `PG*` `libpq` environment variables are set. A local PostgreSQL 17 server is confirmed reachable on `localhost:5432` (`pg_isready` succeeds), but authenticates require a credential this session does not have. No password was guessed, brute-forced, or searched for, consistent with every prior MWO's standing constraint.

---

## What This Report Does and Does Not Claim

**Does claim:**
- The verification infrastructure (discovery, deprecation-skip, timeout-safety, pass/fail accounting, summary reporting, correct non-zero exit code on failure) is real, was exercised end-to-end against this actual environment, and behaved exactly as designed.
- The 10 new Pump/Seal scripts correctly attempt genuine interaction with a real PostgreSQL server — confirmed by the specific, real `fe_sendauth` error each one produces, not a silent no-op or a fabricated result.
- A previously-undiscovered reliability defect (indefinite hang on missing credentials) was found by actually running the tooling, not assumed, and was fixed within this MWO's own new files.
- The product's verification gap has been reduced from "no infrastructure exists to attempt this at all" to "infrastructure exists, works correctly, and needs exactly one input — a reachable, credentialed `LTSA_TEST_DSN`" — a smaller, more specific, more actionable gap than existed before this MWO.

**Does not claim:**
- That any Customer Registry, Pump Registry, or Seal Registry operation has been confirmed correct against live data. Zero scripts produced a genuine pass. No registry's actual behavior was verified by this MWO.
- Full Runtime Verification in any sense broader than database-level SQL execution — no n8n workflow was imported, triggered, or executed at any point.
- That this gap is closed. It is narrower and better-understood than before, not resolved.

---

## PASS / WARNING / BLOCKER

- **Verification Framework, Runner, and Suite (WP-001–WP-003): PASS.** Built, structurally validated, and — as of this report — behaviorally proven against a real environment, including a real defect found and fixed.
- **Actual database-level verification of Customer/Pump/Seal Registry behavior: BLOCKER.** Zero of 16 applicable scripts produced a real result. The blocking condition is precisely identified (missing `LTSA_TEST_DSN`/credential) and is external to this MWO's own deliverables — it is an environment-provisioning gap, not a defect in the infrastructure this MWO built.

## Known Limitations

- This environment's specific inability to supply a database credential is unresolved by this MWO and was never in its scope to resolve (provisioning a credential is a Chief Architect / infrastructure decision, not an implementation task).
- Customer Registry's original 6 test scripts still contain the un-fixed hang-prone pattern. The runner now defends against this generically (60-second timeout), but the scripts themselves remain as MWO-P-003 left them, per this MWO's explicit constraint not to modify Customer Registry.
- No assertion in any of the 16 scripts has ever been confirmed true against real data by any MWO to date, including this one.
