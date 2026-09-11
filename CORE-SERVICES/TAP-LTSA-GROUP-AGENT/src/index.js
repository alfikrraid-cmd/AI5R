/**
 * MWO-LTSA-TAP-GROUP-AGENT-001 -- TAP LTSA WhatsApp Group Agent entry
 * point. Wires a Baileys WhatsApp Web socket to messagePipeline.js's pure
 * classification/trigger functions and httpClient.js's backend call.
 *
 * Status correction (MWO-LTSA-069, 2026-09-11): the comment that used to
 * live here claimed this process only ever reaches an UNPAIRED,
 * WAITING_FOR_PAIRING state (Phase 2B-1), with real pairing a separate,
 * later, human-gated step (Phase 2B-2). A read-only production audit
 * found this to already be false in practice: the deployed container is
 * paired and CONNECTED against a real WhatsApp number, via an auth-state
 * volume that was populated out-of-band (outside any MWO's recorded
 * scope). printQRInTerminal is still false and no handler still ever logs
 * the `qr` value itself -- that part of the original design holds
 * regardless of pairing state.
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
import { decideOnClose } from "./reconnectPolicy.js";

const BACKEND_BASE_URL = process.env.AI5R_BACKEND_BASE_URL;
const INGRESS_SECRET = process.env.AI5R_WHATSAPP_GROUP_INGRESS_SECRET;
const AUTH_STATE_DIR = process.env.TAP_GROUP_AGENT_AUTH_STATE_DIR || "./auth_state";

const MAX_MEDIA_BYTES = 15 * 1024 * 1024;

async function handleIncomingMessage(sock, msg, client, options = {}) {
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

  if (event.media_type) {
    if (typeof event.file_length === "number" && event.file_length > MAX_MEDIA_BYTES) {
      await sock.sendMessage(event.group_id, {
        text: "Ukuran file terlalu besar. Maksimum 15 MB.",
      });
      return;
    }

    let buffer;
    try {
      if (options.downloadMedia) {
        buffer = await options.downloadMedia(msg);
      } else {
        const { downloadMediaMessage } = await import("@whiskeysockets/baileys");
        buffer = await downloadMediaMessage(msg, "buffer", {});
      }
    } catch (downloadErr) {
      await sock.sendMessage(event.group_id, {
        text: "Gagal mengunduh media dari WhatsApp. Silakan kirim ulang dokumen/gambar.",
      });
      return;
    }

    if (!buffer || buffer.length === 0) {
      await sock.sendMessage(event.group_id, {
        text: "Gagal memproses media (file kosong atau tidak terbaca).",
      });
      return;
    }

    if (buffer.length > MAX_MEDIA_BYTES) {
      await sock.sendMessage(event.group_id, {
        text: "Ukuran file terlalu besar. Maksimum 15 MB.",
      });
      return;
    }

    event.media_bytes_base64 = buffer.toString("base64");
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
  const client = createGroupAgentClient({ baseUrl: BACKEND_BASE_URL, ingressSecret: INGRESS_SECRET });

  // MWO-LTSA-069 -- in-process reconnect for transient disconnects (see
  // reconnectPolicy.js for the classification/backoff rules and their
  // rationale). `generation` guards against acting on a "close" event
  // fired by a socket that a later reconnect attempt has already
  // superseded -- connect() is only ever called again after the PREVIOUS
  // socket's own close handling has finished, but this guard also makes
  // it safe if Baileys ever emits a stray/duplicate event on an old
  // socket. `reconnectTimer` guards against ever scheduling two
  // concurrent reconnect attempts.
  let generation = 0;
  let reconnectTimer = null;
  let attempt = 0;

  function connect() {
    const myGeneration = ++generation;
    reconnectTimer = null;
    const sock = makeWASocket({ auth: state, printQRInTerminal: false });

    sock.ev.on("creds.update", saveCreds);
    sock.ev.on("connection.update", (update) => {
      if (myGeneration !== generation) {
        // A stale socket's event, superseded by a later connect() call --
        // never act on it (this is what prevents concurrent
        // reconnect/socket loops).
        return;
      }
      if (update.qr) {
        // Never log update.qr itself -- only that pairing is pending.
        console.log("event=tap_group_agent_status status=WAITING_FOR_PAIRING");
      }
      if (update.connection === "open") {
        console.log("event=tap_group_agent_status status=CONNECTED");
        attempt = 0; // a successful connection resets the backoff counter
      }
      if (update.connection === "close") {
        const statusCode = update.lastDisconnect?.error?.output?.statusCode;
        attempt += 1;
        const decision = decideOnClose(statusCode, attempt);

        if (decision.action === "EXIT_UNRECOVERABLE") {
          // loggedOut/badSession: the on-disk auth state itself is no
          // longer usable. Never delete or modify auth_state here -- that
          // is a human, explicit, out-of-band decision (re-pairing), not
          // something this process does automatically. Exit and let
          // Docker's restart policy be the last-resort recovery; it will
          // keep restarting into this same terminal state until a human
          // acts, which is the correct, visible failure mode (loud, not
          // silently spinning).
          console.log(
            `event=tap_group_agent_status status=UNRECOVERABLE_AUTH_STATE status_code=${decision.statusCode ?? "unknown"}`
          );
          process.exit(1);
          return;
        }

        if (decision.action === "EXIT_ATTEMPTS_EXHAUSTED") {
          console.log(
            `event=tap_group_agent_status status=RECONNECT_ATTEMPTS_EXHAUSTED attempts=${decision.attempts} status_code=${decision.statusCode ?? "unknown"}`
          );
          process.exit(1); // Docker restart is the last-resort recovery here.
          return;
        }

        // RECONNECT: retry in-process with the SAME auth state, bounded
        // exponential backoff, no PII/credentials in the log line.
        console.log(
          `event=tap_group_agent_status status=DISCONNECTED_WILL_RETRY_IN_PROCESS attempt=${decision.attempt} delay_ms=${decision.delayMs} status_code=${decision.statusCode ?? "unknown"}`
        );
        if (reconnectTimer === null) {
          reconnectTimer = setTimeout(connect, decision.delayMs);
        }
      }
    });
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
    return sock;
  }

  connect();
}

// Runs only when this file is executed directly (`node src/index.js`,
// the container's own entrypoint) -- never on import, so
// messagePipeline.test.js / index.test.js (which import
// handleIncomingMessage) never trigger a real Baileys connection.
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("event=tap_group_agent_status status=FATAL_STARTUP_ERROR message=" + error.message);
    process.exit(1);
  });
}

export { handleIncomingMessage };
