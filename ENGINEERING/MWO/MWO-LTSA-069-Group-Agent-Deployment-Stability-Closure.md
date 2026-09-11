# MWO-LTSA-069 — Group Agent Deployment + Stability Closure

Status: **IMPLEMENTED, LOCAL ONLY — independent review PASS, ready for commit; production cutover (Sections 9–11) remains a separate, not-yet-authorized gate**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer, per `CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md`.
Architecture: FROZEN — this MWO formalizes an existing out-of-band deployment into tracked IaC and adds bounded reconnect handling; it introduces no new architecture, pattern, or service beyond what `CORE-SERVICES/TAP-LTSA-GROUP-AGENT/README.md`'s own "Phase 2A — future deployment plan" already specified.
Predecessor evidence: two prior read-only audit passes (AI5R LTSA current-state recovery; MWO-069 pre-implementation evidence gate), both conducted this session, cited throughout below.

---

## Goal

Close the gap between the TAP LTSA WhatsApp Group Agent's actual, verified production state and what the repository's tracked IaC and documentation claimed — without touching production.

## Scope

- Track `tap-ltsa-group-agent` in `CORE-SERVICES/RUNTIME/compose.yaml`.
- Add bounded in-process reconnect handling for the confirmed transient-disconnect crash loop.
- Design (not apply) a migration-applied-state tracking mechanism.
- Correct stale documentation/comments that assert facts contradicted by verified production state.

## Out of scope (per explicit instruction)

- Any production mutation: no SSH beyond bounded read-only verification, no `docker` start/stop/recreate, no `compose up/down`, no DB write/DDL, no migration apply, no WhatsApp re-pairing, no auth-volume change, no commit/push/deploy.
- MWO-LTSA-039A (`LTSAMessagingGateway` / `HOLD_SECURITY_SCOPE_CLOSURE`) — confirmed unrelated, see "MWO-039A Independence" below.
- Any refactor not required to close the above gaps.

---

## 1. Verified Current Production State (evidence, not inference)

All of the following was established by two prior read-only audit passes this session (SSH via PowerShell to `ai5r`, bounded `docker inspect`/`docker logs`/`docker exec … psql` commands only, no mutation):

- **HEAD parity**: local `travel/release-ltsa` and production `release/ltsa-v1-rc1` are both at `3e85b9b7cf98475b1a7f194b49d3ec7044437864`, clean trees (production's untracked artifacts are the known, documented, hands-off baseline).
- **`tap-ltsa-group-agent` container**: running, image `ai5r/tap-ltsa-group-agent:3e85b9b7` (matches HEAD), created 2026-09-09T05:36:35Z, `RestartPolicy=unless-stopped` (unbounded retries), `RestartCount=14` over ~2 days.
- **Deployment method**: bare `docker run`, not `docker compose up` — `Config.Labels={}` (no `com.docker.compose.*` labels), while it is attached to network `ai5ros-prod-edge`, which itself *is* compose-owned (its labels show `com.docker.compose.project=ai5ros-prod`). I.e., a human ran `docker run --network ai5ros-prod-edge …` by hand.
- **Auth state**: volume `tap_ltsa_group_agent_auth_state` → `/app/auth_state`, created 2026-09-04 (5 days before this container instance) — holds live, valid Baileys credentials for a real, already-paired WhatsApp number. This is the single most important fact governing every decision below: this volume must never be lost, recreated, or renamed.
- **Crash loop**: confirmed via `RestartCount=14` plus repeated `logging in… → 11 pre-keys found → opened connection to WA → CONNECTED` cycles in `docker logs` (a true process restart each time, not an in-process reconnect).
- **Trigger**: on every sampled cycle, ~60–70s after `CONNECTED`, Baileys throws `Timed Out` in `executeInitQueries → fetchProps`, later followed by a socket-level `Connection Terminated` / `Stream Errored`, at which point `src/index.js`'s (pre-MWO-069) `connection.update` "close" handler logged `DISCONNECTED_WILL_RESTART` and called `process.exit(0)`, relying entirely on Docker's `unless-stopped` policy to relaunch.
- **Authorization**: `public.whatsapp_group_authorization` and `public.whatsapp_group_message_seen` (migration 032's tables) **already exist in production** `ltsa_brain`, containing 2 real `ACTIVE` groups ("LTSA group", "LTSA Group 2") and 45 real dedupe-ledger rows — despite every piece of repository documentation for this feature (the migration's own header, `whatsapp_group_repository_inmemory.py`'s docstring, `whatsapp_group_agent_service.py`'s comment, `dependencies.py`'s comment, `TAP-LTSA-GROUP-AGENT/README.md`) asserting this was not applied/not deployed.
- **Enforcement**: `CORE-SERVICES/BACKEND-API/dependencies.py:676-678` wires the real, Postgres-backed `WhatsAppGroupAuthorizationRepository` into the live FastAPI dependency graph (confirmed by direct code read) — not the in-memory Phase-1 fallback that some of the same stale comments implied was still the only thing wired.
- **"Rizky"**: no evidence found anywhere that this name is an authorized identity. The two ACTIVE groups' `registered_by`/`activated_by` is a single user UUID (`bf3d895f-23af-45fa-b5af-e4219ca0add1`) whose `username` column is blank; "Rizky" appears in the codebase only as unrelated Installation Report sample/test fixture data (`AI5R-STUDIO/dashboard/src/modules/ltsa/data/sampleInstallations.js`, several test files).

## 2. Deployment Drift

No compose fragment for this service existed anywhere in the repository before this MWO (only a Dockerfile, `CORE-SERVICES/RUNTIME/docker/group-agent.Dockerfile`, and a prose "future deployment plan" in the README). The out-of-band `docker run` that is actually live in production must have supplied, at minimum: `--network ai5ros-prod-edge`, `-v tap_ltsa_group_agent_auth_state:/app/auth_state`, `--restart unless-stopped`, and the three env vars below — this MWO's compose entry (Section 4) reconstructs exactly that configuration from the running container's own inspected state, not from guesswork.

## 3. Authorization Reality

Migration 032's effect is live and actively enforced (Section 1). The gap is **not** "authorization is unimplemented" — it is that nothing in the repository could tell an operator this, and no mechanism exists to know whether any *other* migration (005–031, 033) is applied. Section 6 addresses this.

## 4. Persistent-State Requirement

Two things must survive any future recreation of this deployment, in order of severity:

1. **Docker volume `tap_ltsa_group_agent_auth_state`** — loses the live WhatsApp pairing if replaced. This MWO's compose entry declares it `external: true` under its exact literal name (not the `${AI5R_VOLUME_PREFIX}`-prefixed pattern every other volume in `compose.yaml` uses), so `docker compose up` **refuses to run** if the volume is missing rather than silently creating an empty one.
2. **Postgres `ltsa_brain.whatsapp_group_authorization` / `.whatsapp_group_message_seen` rows** — already safe, since they live in the shared, already-compose-managed `postgres` service, unaffected by this container's own lifecycle. Called out in `PRODUCTION_VOLUME_MAPPING.md` and this document so a future migration-tracking cleanup doesn't truncate them by mistake.

## 5. Crash-Loop Evidence

See Section 1's "Crash loop" / "Trigger" bullets. Additional root-cause investigation (Phase C, this MWO):

- **Baileys version**: pinned `6.7.24` is already the **latest stable release** (published 2026-07-29, per `npm view`). The only newer track is `7.0.0-rc.1`–`7.0.0-rc14`, all pre-release. **No version bump is justified** — there is no newer stable release, and adopting an RC line for a production WhatsApp session is not warranted by the evidence.
- **Known issue class, not a local misconfiguration**: `WhiskeySockets/Baileys` GitHub issues include open, recent reports of the same symptom class (`#2491` "sessions go deaf after 30+ minutes", `#2477` "protocol rejection during props initialization", both 2026) and a closed 2025 issue with the identical error string (`#977`, "unexpected error in init queries") with no documented root cause or fix in the library itself. This confirms the previous design's own instinct (treat it as expected, not a bug to chase) while showing the fix belongs in *this service's* resilience, not in a dependency bump.

## 6. Migration Tracking (design only — not applied)

New migration `PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/034_create_schema_migration_history.sql` creates `public.schema_migration_history` (migration_file, status ∈ {CONFIRMED_APPLIED, ASSUMED_APPLIED_SEQUENTIAL, UNKNOWN}, applied_at nullable, recorded_at, recorded_by, verification_note). Companion `034_KNOWN_MIGRATION_STATE.md` records, honestly: 005–031 `UNKNOWN` (out of this MWO's scope to check), 032 `CONFIRMED_APPLIED` (cited evidence above), 033 `UNKNOWN`, 034 not yet applied anywhere. **Not applied to production by this MWO** — the file and manifest exist so a future, explicitly-authorized operator action can apply the schema and backfill it, per the manifest's own "Operator Action" section. No historical `applied_at` timestamp is fabricated anywhere.

Stale-doc corrections applied (dated, additive corrections — original text preserved for audit-trail purposes, not deleted) in: `032_create_whatsapp_group_authorization.sql`, `whatsapp_group_repository_inmemory.py`, `whatsapp_group_agent_service.py`, `dependencies.py`, `TAP-LTSA-GROUP-AGENT/README.md`.

## 7. MWO-039A Independence

Confirmed unrelated by citation, not inference: MWO-039A concerns `CORE-SERVICES/API/ltsa_messaging_gateway.py` (`LTSAMessagingGateway`, a fleet-summary orchestrator explicitly built with "no HTTP client, no SQL, no WhatsApp SDK"), held (`HOLD_SECURITY_SCOPE_CLOSURE`, per `ENGINEERING/IT-AGENT/MEMORY/risks.md` and `unresolved-tasks.md`) over an area/MA data-scope gap in `get_fleet_summary()`. Grep confirms `ltsa_messaging_gateway` is imported nowhere outside its own test file; `deployment-history.md` confirms it "was NOT part of" the release merge. It has no import relationship with the group agent's authorization code (`whatsapp_group_repository_postgres.py`, `dependencies.py`). **This MWO does not depend on MWO-039A being resolved, and does not touch `ltsa_messaging_gateway.py`.**

## 8. Rollback Requirements

If any part of this MWO's compose entry is ever wrong and must be rolled back:
- Reverting `compose.yaml`'s new `tap-ltsa-group-agent` service block and the `group_agent_auth_state` volume declaration is a pure file revert — the out-of-band container this MWO formalizes keeps running exactly as it does today, untouched, since **no `docker compose up` was run against this change**.
- The `external: true` volume declaration means even a future, mistaken `docker compose up` cannot silently create a fresh empty volume in place of the real one — it will fail loudly instead, which is the intended safety property, not a bug to work around.
- Reverting the reconnect-policy code (`src/index.js`, `src/reconnectPolicy.js`) restores the original exit-on-close/Docker-restart behavior; it is a pure code revert with no data-migration implication (no schema, no persisted state introduced by that change).
- Reverting migration `034` and its manifest is safe at any time before `034` is actually applied to any database (it has not been, by this MWO or otherwise, as far as this audit could determine).

## 9. Production Handover Safety (Cutover Procedure)

Added at Chief-Architect-independent-review request, 2026-09-11. **Not executed by this MWO — documentation only, no production mutation.**

The bare out-of-band container (Section 1/2) and the now-tracked `compose.yaml` service definition (Section 4) describe the SAME logical agent, but they are two independently startable things. Running `docker compose up` while the bare container is still running is a **dual-mount hazard**, not merely redundant:

- Both the bare container and a freshly-started compose-managed `tap-ltsa-group-agent` reference the identical Docker volume name (`tap_ltsa_group_agent_auth_state`) mounted at `/app/auth_state`. Docker permits the same named volume to be mounted read-write into two containers simultaneously — nothing in Docker itself prevents this.
- Baileys' `useMultiFileAuthState` treats that directory as a single-writer session store (credential/session files it both reads at startup and rewrites via `saveCreds` on every `creds.update`). Two Baileys processes reading and writing the same auth-state files concurrently is **not a supported configuration** — at minimum it risks two sockets racing to present the same paired session to WhatsApp (each believing it is the sole active device-linked client), corrupted/interleaved writes to the auth-state files, and — in the worst case — WhatsApp's own multi-device conflict handling logging the paired number out entirely (an `UNRECOVERABLE` state per `reconnectPolicy.js`, requiring human re-pairing).
- **Concurrent Baileys use of the same auth state is therefore prohibited.** At no point during cutover may both the bare container and the compose-managed container be running against this volume at the same time.

### Required Cutover Sequence

Each step is a distinct, verified gate — do not proceed to the next until the current one is confirmed. This sequence is the Chief-Architect-approved procedure for a future, separately-authorized production action; it is recorded here so that action, when taken, has an unambiguous script to follow.

1. **Verify current container/image.** `docker inspect tap-ltsa-group-agent` — confirm the running image digest/tag and `RestartCount` match what this MWO's evidence (Section 1) recorded, before changing anything. If they differ, STOP and re-audit — the live state has moved since this MWO was written.
2. **Controlled stop of the bare container.** `docker stop tap-ltsa-group-agent`. This releases its mount on `tap_ltsa_group_agent_auth_state` without deleting the container or the volume.
3. **DO NOT remove it.** No `docker rm`. The stopped bare container is the rollback target (Section 11) until the compose-managed replacement is independently confirmed healthy.
4. **Start ONLY the compose-managed service.** `docker compose up -d tap-ltsa-group-agent` (scoped to this one service, not a full-stack `up`, to avoid incidentally touching the other 8 already-running services). This is the first and only moment a second process may touch the auth-state volume, and only because step 2 already released it.
5. **Verify exactly one agent.** `docker ps --filter name=tap-ltsa-group-agent` must show exactly one running container, and it must be the compose-managed one (`docker inspect --format '{{json .Config.Labels}}'` should now show `com.docker.compose.*` labels, unlike the bare container's empty `{}`).
6. **Verify CONNECTED.** Tail its logs for `event=tap_group_agent_status status=CONNECTED` (the same structured log line this MWO's reconnect logic already emits) — not merely "container running."
7. **Test authorized `/ltsa`.** From one of the 2 confirmed-`ACTIVE` groups (Section 1), send a real `/ltsa <question>` message and confirm a reply — proof the authorization wiring (Section 3) and the message pipeline both survived the cutover, not just the socket connection.
8. **Observe reconnect/restart behavior.** Watch at least one full disconnect/reconnect cycle (the known `fetchProps` timeout, Section 5, recurs roughly hourly) and confirm the new structured logs (`DISCONNECTED_WILL_RETRY_IN_PROCESS attempt=… delay_ms=…`) appear instead of the old `DISCONNECTED_WILL_RESTART` / full process exit — this is the actual, observable proof that MWO-069's reconnect design (Section "Reconnect Design") is running, not just deployed.

Only after all 8 steps are confirmed is the bare container's continued existence purely a rollback safety net rather than an active, competing WhatsApp session.

## 10. Image Strategy

Resolved in documentation only — no change to `compose.yaml` by this update (that file already carries `image: ${AI5R_GROUP_AGENT_IMAGE_REPO}:${AI5R_VERSION}` from Section 4's original implementation, unmodified here).

**Decision:** production cutover for this service MUST use an immutable image reference pinned to the exact git SHA of the reviewed commit — the same pattern already visible in the currently-running bare container's own image tag, `ai5r/tap-ltsa-group-agent:3e85b9b7`. This service must **never** cut over on a floating/shared tag.

Rationale: `${AI5R_VERSION}` (currently `0.1.0` per `.env.example`) is a single value shared across `dashboard`, `api`, and now this service — bumping it for an unrelated dashboard or API release would silently roll this service onto a different, unreviewed build of the group agent, against a live, already-paired WhatsApp session, with no independent review gate for that specific change. A floating tag is an acceptable convention for the other services precisely because their releases don't carry this MWO's dual-mount and re-pairing risk.

**How an operator satisfies this without a compose.yaml change:** at cutover time, set the operator's own `.env` `AI5R_VERSION` to the exact reviewed commit's short SHA (e.g. `AI5R_VERSION=3e85b9b7`) before running `docker compose up -d tap-ltsa-group-agent` (Section 9, step 4) — this is a deploy-time value, not a code change, and satisfies "pin to an immutable SHA" using the existing `${AI5R_GROUP_AGENT_IMAGE_REPO}:${AI5R_VERSION}` reference without inventing a service-specific override mechanism. Any future MWO that wants a per-service pinning mechanism independent of the shared `AI5R_VERSION` value is a separate, explicit architecture decision, not made here.

## 11. Rollback Sequence

The inverse of Section 9, invoked if the compose-managed agent is unhealthy, fails verification, or misbehaves after cutover:

1. **Stop the compose-managed group-agent.** `docker compose stop tap-ltsa-group-agent` (stop, not `down` / `rm` — no need to remove its definition, only to release the volume).
2. **Ensure it is fully stopped.** `docker ps --filter name=tap-ltsa-group-agent` must show no running compose-managed container before proceeding — do not start the rollback target while any writer to the auth-state volume might still be shutting down.
3. **Restart the preserved bare container using its original image/config.** `docker start tap-ltsa-group-agent` (the SAME container object preserved, not recreated, in Section 9 step 3) — this is why step 3 there forbade `docker rm`: a `docker start` on the original container reuses its exact original image, env, network, and volume mount with zero reconstruction risk, whereas re-deriving an equivalent `docker run` command from memory would not carry the same guarantee.
4. **Never run both simultaneously** — same dual-mount prohibition as Section 9, in reverse: do not `docker start` the bare container until step 2 has confirmed the compose-managed one is fully stopped.
5. **Preserve the auth volume throughout.** No step in this sequence touches, recreates, or removes `tap_ltsa_group_agent_auth_state` — rollback only changes which single container is attached to it.

## 12. Known Gaps Not Addressed By This MWO (explicitly out of scope)

- The Baileys `fetchProps`/init-queries timeout itself is not fixed — only made resilient to. If WhatsApp-side or Baileys-side behavior changes, this may need revisiting.
- No healthcheck is defined for this service, matching the running container's own actual configuration (`Config.Healthcheck` = `null`) — Baileys is an outbound client, not an HTTP server, so none was fabricated.
- 005–031 and 033's applied-state remain `UNKNOWN` — this MWO only closes the tracking *mechanism* gap, not the historical-knowledge gap for those specific files.
- Sections 9–11 are a documented procedure, not an executed one — this MWO performed no production mutation of any kind (per its own scope) and the actual cutover remains a separate, explicitly-authorized future action.
