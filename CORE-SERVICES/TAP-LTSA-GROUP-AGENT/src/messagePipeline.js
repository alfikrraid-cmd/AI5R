/**
 * MWO-LTSA-TAP-GROUP-AGENT-001 -- pure functions over a Baileys WAMessage
 * object. Zero I/O, zero Baileys import, zero LTSA logic here -- this
 * module only decides WHAT an inbound event structurally is (group vs
 * personal, self vs not, triggered vs ordinary chatter) and normalizes it
 * into the same shape the backend's GroupMessageEvent expects. All
 * authorization/routing/LTSA decisions happen server-side
 * (whatsapp_group_agent_service.py) -- this file must never grow an
 * authorization check of its own.
 *
 * Baileys WAMessage shape relied on here (stable across the pinned
 * 6.7.24 release):
 *   msg.key.remoteJid   - the chat JID; ends in "@g.us" for a group,
 *                          "@s.whatsapp.net" for a personal chat
 *   msg.key.participant - the ACTUAL sender's JID, present only on group
 *                          messages (remoteJid is the GROUP, never the
 *                          sender, for a group message -- this is exactly
 *                          why group id and sender id must be read from
 *                          two different fields, never conflated)
 *   msg.key.id          - the provider message id
 *   msg.key.fromMe      - true when this transport's own linked account
 *                          sent the message
 *   msg.message.conversation /
 *   msg.message.extendedTextMessage.text - the plain text body
 *   msg.messageTimestamp - unix seconds (may be a Long-like object)
 */

const TRIGGER_RE = /^\s*\/ltsa\b/i;

/** True only for a message Baileys attributes to this transport's own
 * linked account -- checked first, before any other classification. */
export function isFromSelf(msg) {
  return Boolean(msg?.key?.fromMe);
}

/** A group chat JID always ends in "@g.us" in the Baileys/WhatsApp
 * protocol; anything else (personal 1:1, "@s.whatsapp.net") is not a
 * group message for this agent's purposes. */
export function isGroupMessage(msg) {
  const remoteJid = msg?.key?.remoteJid;
  return typeof remoteJid === "string" && remoteJid.endsWith("@g.us");
}

/** The group's own identity -- remoteJid, and ONLY remoteJid. Never the
 * sender's participant id. */
export function extractGroupId(msg) {
  return msg?.key?.remoteJid ?? null;
}

/** The actual individual sender. For a group message this is
 * key.participant (never remoteJid, which is the group). For a personal
 * message Baileys does not set participant at all -- remoteJid IS the
 * individual in that case, but this agent only ever processes group
 * messages, so a missing participant on a message this module already
 * classified as a group message is treated as malformed (returns null,
 * never falls back to remoteJid -- that would silently misattribute the
 * sender as the group). */
export function extractSenderId(msg) {
  if (!isGroupMessage(msg)) return null;
  return msg?.key?.participant ?? null;
}

export function extractProviderMessageId(msg) {
  return msg?.key?.id ?? null;
}

export function extractText(msg) {
  const body = msg?.message?.conversation ?? msg?.message?.extendedTextMessage?.text ?? "";
  return typeof body === "string" ? body : "";
}

export function extractTimestamp(msg) {
  const ts = msg?.messageTimestamp;
  if (ts === undefined || ts === null) return null;
  // Baileys sometimes returns a Long-like object ({low, high, unsigned})
  // instead of a plain number depending on the underlying proto decode;
  // only trust a value that is already a genuine JS number.
  return typeof ts === "number" ? ts : null;
}

/**
 * Returns the question text (possibly "") if `text`'s first non-whitespace
 * token is literally "/ltsa" (case-insensitive), else null. Identical
 * rule to the backend's own extract_ltsa_trigger() in
 * whatsapp_group_agent_service.py -- kept as two independent
 * implementations (Python owns the authorization-relevant decision when
 * the backend call actually happens; this one is only a cheap local
 * pre-filter so ordinary group chatter never leaves this process at all)
 * but deliberately identical in behavior test-for-test.
 */
export function extractLtsaTrigger(text) {
  if (!text) return null;
  const match = TRIGGER_RE.exec(text);
  if (!match) return null;
  return text.slice(match[0].length).trim();
}

/**
 * Normalizes one Baileys WAMessage into the plain-object shape the
 * backend's /api/ltsa/whatsapp-group/message endpoint expects. Returns
 * null if the message is not something this agent should even consider
 * forwarding (not from a group, or missing a field the backend requires)
 * -- callers must check for null before doing anything else, matching
 * the "terminate before any network call" performance requirement.
 */
export function normalizeGroupMessageEvent(msg) {
  if (isFromSelf(msg)) return null;
  if (!isGroupMessage(msg)) return null;

  const groupId = extractGroupId(msg);
  const senderId = extractSenderId(msg);
  const providerMessageId = extractProviderMessageId(msg);
  if (!groupId || !senderId || !providerMessageId) return null;

  return {
    group_id: groupId,
    sender_identifier: senderId,
    provider_message_id: providerMessageId,
    text: extractText(msg),
    is_from_self: false,
  };
}
