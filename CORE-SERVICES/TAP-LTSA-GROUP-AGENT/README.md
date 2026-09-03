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
