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
 *                          two different fields, never conflated). In a
 *                          group where WhatsApp's LID (Linked ID) privacy
 *                          feature is active, this may be a "@lid"
 *                          pseudonym instead of the classic phone-based
 *                          "@s.whatsapp.net" JID.
 *   msg.key.participantPn - Baileys' own phone-based alternative for a
 *                          "@lid" participant, when it has one to offer
 *                          (undefined otherwise, including for every
 *                          already-phone-based participant). Backend
 *                          authorization hashes a normalized PHONE
 *                          NUMBER (see whatsapp_intake_service.
 *                          normalize_sender_identifier); a raw "@lid"
 *                          value hashes to digits that were never
 *                          registered by anyone, which is exactly why an
 *                          otherwise-ACTIVE, correctly-registered sender
 *                          can still be told "Nomor Anda belum memiliki
 *                          akses LTSA" -- see extractSenderId below.
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

/** True only for a WhatsApp LID (Linked ID) participant JID -- see the
 * module header's note on msg.key.participantPn. */
function isLidJid(jid) {
  return typeof jid === "string" && jid.endsWith("@lid");
}

/** A deliberately narrow shape check -- never trusts a malformed, empty,
 * or non-phone-shaped participantPn as a stand-in identifier. Anything
 * that fails this is treated exactly as if participantPn were absent. */
function isPhoneJid(jid) {
  return typeof jid === "string" && jid.trim() !== "" && jid.endsWith("@s.whatsapp.net");
}

/** The actual individual sender. For a group message this is normally
 * key.participant (never remoteJid, which is the group). For a personal
 * message Baileys does not set participant at all -- remoteJid IS the
 * individual in that case, but this agent only ever processes group
 * messages, so a missing participant on a message this module already
 * classified as a group message is treated as malformed (returns null,
 * never falls back to remoteJid -- that would silently misattribute the
 * sender as the group).
 *
 * LID resolution: when participant is itself a "@lid" pseudonym AND
 * Baileys supplies a genuinely phone-shaped participantPn alternative,
 * that alternative is returned instead -- server-side authorization
 * already hashes a normalized phone number, so this is what lets an
 * otherwise-correctly-registered, ACTIVE sender actually resolve. This
 * function performs no authorization decision of its own (that remains
 * exclusively server-side, per this module's own header rule): a "@lid"
 * participant with no usable phone alternative still returns the raw
 * "@lid" value, completely unchanged from prior behavior -- it will
 * still fail the backend's hash lookup exactly as it does today, never
 * granting access on the strength of the LID itself. */
export function extractSenderId(msg) {
  if (!isGroupMessage(msg)) return null;
  const participant = msg?.key?.participant ?? null;
  if (isLidJid(participant) && isPhoneJid(msg?.key?.participantPn)) {
    return msg.key.participantPn;
  }
  return participant;
}

export function extractProviderMessageId(msg) {
  return msg?.key?.id ?? null;
}

export function unwrapMessage(msg) {
  let m = msg?.message;
  while (m) {
    if (m.ephemeralMessage?.message) {
      m = m.ephemeralMessage.message;
    } else if (m.viewOnceMessage?.message) {
      m = m.viewOnceMessage.message;
    } else if (m.viewOnceMessageV2?.message) {
      m = m.viewOnceMessageV2.message;
    } else if (m.documentWithCaptionMessage?.message) {
      m = m.documentWithCaptionMessage.message;
    } else {
      break;
    }
  }
  return m ?? null;
}

export function extractMediaInfo(msg) {
  const m = unwrapMessage(msg);
  if (!m) return null;
  if (m.imageMessage) {
    const img = m.imageMessage;
    const len = img.fileLength !== undefined && img.fileLength !== null ? Number(img.fileLength) : null;
    return {
      media_type: "image",
      mimetype: typeof img.mimetype === "string" ? img.mimetype : "image/jpeg",
      filename: typeof img.fileName === "string" ? img.fileName : "image.jpg",
      file_length: Number.isFinite(len) ? len : null,
    };
  }
  if (m.documentMessage) {
    const doc = m.documentMessage;
    const len = doc.fileLength !== undefined && doc.fileLength !== null ? Number(doc.fileLength) : null;
    return {
      media_type: "document",
      mimetype: typeof doc.mimetype === "string" ? doc.mimetype : "application/octet-stream",
      filename: typeof doc.fileName === "string" ? doc.fileName : "document.pdf",
      file_length: Number.isFinite(len) ? len : null,
    };
  }
  return null;
}

export function extractText(msg) {
  const m = unwrapMessage(msg);
  if (!m) return "";
  const body =
    m.conversation ??
    m.extendedTextMessage?.text ??
    m.imageMessage?.caption ??
    m.documentMessage?.caption ??
    "";
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

  const mediaInfo = extractMediaInfo(msg);
  const event = {
    group_id: groupId,
    sender_identifier: senderId,
    provider_message_id: providerMessageId,
    text: extractText(msg),
    is_from_self: false,
  };

  if (mediaInfo) {
    event.media_type = mediaInfo.media_type;
    event.mimetype = mediaInfo.mimetype;
    event.filename = mediaInfo.filename;
    if (mediaInfo.file_length !== null) {
      event.file_length = mediaInfo.file_length;
    }
  }

  return event;
}
