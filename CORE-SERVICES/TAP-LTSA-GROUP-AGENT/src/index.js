/**
 * MWO-LTSA-TAP-GROUP-AGENT-001 -- TAP LTSA WhatsApp Group Agent entry
 * point. Wires a Baileys WhatsApp Web socket to messagePipeline.js's pure
 * classification/trigger functions and httpClient.js's backend call.
 *
 * PHASE 1: THIS FILE IS NOT RUN. No real WhatsApp number is paired, no
 * QR code is generated, no message is sent, in Phase 1 -- see this
 * feature's own README.md. It exists so the wiring itself is reviewable
 * and so a later phase's "pair a real number" step is a config/ops
 * action, not a code change.
 *
 * Isolation: this process is entirely separate from the existing Meta
 * WhatsApp Business Cloud API personal-chat flow (a different language,
 * a different runtime, a different network boundary). Its crash,
 * disconnect, or absence has no code-level path back into
 * whatsapp_webhook.py, whatsapp_intake_service.py, the FastAPI app, the
 * dashboard, Postgres, or n8n -- the only connection to the rest of AI5R
 * is the one outbound HTTP call in httpClient.js, to one new, isolated,
 * ingress-secret-gated endpoint that itself changes none of those
 * systems' existing behavior.
 */
import { createGroupAgentClient } from "./httpClient.js";
import { extractLtsaTrigger, normalizeGroupMessageEvent } from "./messagePipeline.js";

const BACKEND_BASE_URL = process.env.AI5R_BACKEND_BASE_URL;
const INGRESS_SECRET = process.env.AI5R_WHATSAPP_GROUP_INGRESS_SECRET;
const AUTH_STATE_DIR = process.env.TAP_GROUP_AGENT_AUTH_STATE_DIR || "./auth_state";

async function handleIncomingMessage(sock, msg, client) {
  const event = normalizeGroupMessageEvent(msg);
  if (event === null) {
    // Not a group message, a self-message, or structurally incomplete --
    // terminate here. No log of message content, no network call.
    return;
  }

  const question = extractLtsaTrigger(event.text);
  if (question === null) {
    // Ordinary group chatter: ignored silently, per the mission's own
    // rule -- no AI/DB lookup, no acknowledgement, no reply, and the
    // message body is never logged or forwarded anywhere past this
    // point. This is the cheap fast path: a regex test, nothing else.
    return;
  }

  // Only a message that already passed the local trigger check ever
  // leaves this process. All actual authorization (group allowlist,
  // sender identity, scope) happens server-side and is re-resolved on
  // every single call -- this transport holds no authorization state of
  // its own to cache or get stale.
  let result;
  try {
    result = await client.sendGroupMessage(event);
  } catch (error) {
    // Network/backend failure: safe, generic, non-leaking reply only --
    // never the raw error, host, or stack.
    await sock.sendMessage(event.group_id, { text: "LTSA sedang tidak tersedia. Silakan coba lagi nanti." });
    return;
  }

  if (result.ack) {
    await sock.sendMessage(event.group_id, { text: result.ack });
  }
  if (result.reply) {
    // Always the SAME group the event came from -- event.group_id is the
    // one and only destination this function ever uses; nothing from
    // `result` (the backend's own answer text) or `msg` (quoted/forwarded
    // metadata) can ever substitute for it.
    await sock.sendMessage(event.group_id, { text: result.reply });
  }
}

async function main() {
  if (!BACKEND_BASE_URL || !INGRESS_SECRET) {
    throw new Error(
      "AI5R_BACKEND_BASE_URL and AI5R_WHATSAPP_GROUP_INGRESS_SECRET must be set -- refusing to start without them"
    );
  }

  // Deferred import: Baileys itself is only required at actual runtime,
  // never at test-collection time, so messagePipeline.test.js can run
  // (and does run, in CI) without needing this dependency resolved or
  // any session/QR flow touched.
  const { default: makeWASocket, useMultiFileAuthState } = await import("@whiskeysockets/baileys");

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_STATE_DIR);
  const sock = makeWASocket({ auth: state, printQRInTerminal: false });
  const client = createGroupAgentClient({ baseUrl: BACKEND_BASE_URL, ingressSecret: INGRESS_SECRET });

  sock.ev.on("creds.update", saveCreds);
  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      try {
        await handleIncomingMessage(sock, msg, client);
      } catch (error) {
        // A single malformed/unexpected event must never crash the whole
        // transport process (which would also drop every other group it
        // serves) -- fail closed on that one message only.
      }
    }
  });
}

// Phase 1: intentionally not invoked. Uncomment only after an explicit,
// separate, human-approved pairing step (see README.md) -- this file
// must never auto-connect on import/require.
// main();

export { handleIncomingMessage };
