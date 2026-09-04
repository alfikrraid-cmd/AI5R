# TAP LTSA WhatsApp Group Agent

MWO-LTSA-TAP-GROUP-AGENT-001 — Phase 1 (build + test only).

Lets authorized TAP personnel inside authorized WhatsApp groups ask LTSA /
Equipment360 questions with `/ltsa <question>`. Reuses the existing LTSA
Copilot engine (`API.copilot_orchestrator.orchestrate_copilot`, the exact
function the dashboard's own `/api/ltsa/copilot/ask` endpoint calls) via a
new, isolated backend endpoint. Does not implement any LTSA reasoning
itself.

## ⚠️ Unofficial transport — read before touching this in Phase 2+

This service uses **[Baileys](https://github.com/WhiskeySockets/Baileys)**
(`@whiskeysockets/baileys`, pinned `6.7.24`, MIT license), which automates
the **consumer WhatsApp Web protocol**. It is **not** Meta's official
WhatsApp Business Platform / Cloud API — the existing personal-chat flow
(`CORE-SERVICES/BACKEND-API/routers/whatsapp_webhook.py`) already uses
that official API and is completely untouched by this service.

Consequences of using an unofficial transport, disclosed explicitly, not
hidden:

- **Terms of Service risk**: operating WhatsApp through an unofficial
  client can violate WhatsApp's own Terms of Service. The number paired
  to this transport carries a real risk of being banned or rate-limited
  by WhatsApp, with no official appeal path (unlike the Cloud API's
  business support channel).
- **No official support/SLA**: Baileys is a community-maintained,
  reverse-engineered client. Protocol changes on WhatsApp's side can
  break it without notice.
- **Weaker provenance guarantee than the Cloud API**: the personal-chat
  flow's inbound webhook is Meta-signed (`X-Hub-Signature-256`) end to
  end. This transport has no equivalent third-party signature — message
  authenticity rests on the WhatsApp protocol session itself, not on a
  cryptographic guarantee AI5R can independently verify at the HTTP
  boundary.
- **A separate phone number is required.** A number already registered
  with the Meta Cloud API cannot simultaneously be paired to this
  transport — they are different account modes.

This is a business/compliance decision, made and accepted by the
organization for this specific, isolated group-agent feature — it does
not change the risk posture of the existing, compliant personal-chat
flow in any way.

## Phase 1 constraints (see MWO for full detail)

- **No real number pairing.** `src/index.js`'s `main()` is defined but
  never invoked. Importing this package does not open a WhatsApp
  connection, generate a QR code, or touch any real session.
- **No production deployment.**
- Tests (`npm test`) exercise only pure functions and fakes — no
  network, no real Baileys socket.

## Session material

Baileys session/credential files (written under `auth_state/` once a
real pairing is performed in a later phase) are **git-ignored** — see
`.gitignore` in this directory — and must never be committed, logged, or
included in any bug report. They are equivalent in sensitivity to a
long-lived login session for the paired number.

## Architecture

```
WhatsApp group
    -> Baileys socket (this service, src/index.js)
    -> src/messagePipeline.js   (local, free: self/group/trigger checks)
    -> src/httpClient.js        (only for an actual /ltsa trigger)
    -> AI5R backend: POST /api/ltsa/whatsapp-group/message
       (ingress-secret-gated, separate secret from the personal flow)
    -> group + sender authorization, scope intersection
    -> existing orchestrate_copilot()
    -> reply routed back to the SAME originating group only
```

## License

This package: UNLICENSED (internal AI5R use only).
`@whiskeysockets/baileys`: MIT.

## Phase 2A — production persistence design (not yet deployed)

### Group authorization + dedupe: now Postgres-backed
`dependencies.py`'s `get_group_authorization_repository()` now returns
`WhatsAppGroupAuthorizationRepository` (`CORE-SERVICES/API/whatsapp_group_repository_postgres.py`),
backed by the same shared `DatabaseRunner` singleton every other
direct-DB repository in this codebase already uses. Schema:
`PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/032_create_whatsapp_group_authorization.sql`
— **not applied to any database yet**; an explicit migration-apply step
is required before this feature can be exercised for real.

### Rate limiter: intentionally still process-local (Phase 2A)
`InMemoryRateLimiter` remains in-memory. This is acceptable **only** for
a single-instance deployment: a process restart resets counters to zero,
which can only ever make the limiter *more* permissive for a brief
window, never less — a fail-safe direction, not a security gap. If this
service is ever scaled to multiple instances, this limiter must move to
a shared backend (e.g. Redis) first; documented here so this isn't
silently forgotten.

### Baileys session storage: production volume/mount strategy
- **Volume**: a named, persistent Docker volume (e.g.
  `tap_ltsa_group_agent_auth_state`) mounted at the path
  `TAP_GROUP_AGENT_AUTH_STATE_DIR` points to (default `./auth_state`) —
  **outside the image layer**, so a container recreation (new image,
  redeploy) does not lose the paired session, only a volume deletion
  would.
- **Permissions**: the volume's host-side directory must be owner-only
  (`chmod 700`) and owned by the service's own dedicated, non-root
  container user — never world- or group-readable. Never bind-mounted
  into any other container.
- **Never logged**: `.gitignore` already excludes `auth_state/`; no
  application log statement anywhere in `src/` reads or prints its
  contents. The QR code (produced by Baileys only during an explicit,
  human-initiated pairing step) must be surfaced through a dedicated,
  short-lived, human-attended channel (e.g. a one-time terminal prompt
  during pairing) — **never** through the normal application logs or any
  log-aggregation pipeline. Not implemented in this phase since pairing
  itself does not happen in this phase.

## Phase 2A — future deployment plan (not executed; no pairing, no QR)

A new, independent unit, isolated from the API/dashboard/Meta WhatsApp:

- **Process/container**: its own container (`tap-ltsa-group-agent`),
  built from `CORE-SERVICES/TAP-LTSA-GROUP-AGENT/`, no shared process
  with the FastAPI `api` container.
- **Restart policy**: `restart: unless-stopped`, matching every other
  service in `CORE-SERVICES/RUNTIME/compose.yaml`.
- **Health visibility**: a lightweight liveness signal (e.g. a periodic
  log line or a tiny internal HTTP endpoint reporting Baileys connection
  state) distinct from the `api` container's own healthcheck — this
  service's health must never be conflated with API/dashboard health.
- **Persistent volume**: the named `auth_state` volume above.
- **Isolated secrets**: `AI5R_WHATSAPP_GROUP_INGRESS_SECRET` (already
  used, distinct from every personal-flow secret) plus whatever Baileys
  itself needs — none shared with Meta Cloud API credentials
  (`WHATSAPP_CLOUD_API_TOKEN`, `META_APP_SECRET`) or any other service.
- **No public port**: this service only makes one *outbound* HTTP call
  (to the existing API's internal endpoint); it accepts no inbound
  connections from outside the WhatsApp protocol itself, so no port
  needs to be published/exposed.
- **Failure isolation**: its only coupling to the rest of AI5R is that
  one outbound HTTP call — a crash, disconnect, or absence has no code
  path back into the API, dashboard, Postgres, n8n, or the Meta
  WhatsApp personal flow (verified in Phase 1: zero diff against any of
  those files; unchanged in Phase 2A).

This plan is **not executed** in Phase 2A: no container is built or run
for this service, no number is paired, no QR is generated.
