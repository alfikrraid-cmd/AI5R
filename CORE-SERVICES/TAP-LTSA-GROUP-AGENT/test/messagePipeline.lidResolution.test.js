import assert from "node:assert/strict";
import { test } from "node:test";

import { extractSenderId, normalizeGroupMessageEvent } from "../src/messagePipeline.js";

// AI5R-WHATSAPP-LID-SENDER-RESOLUTION-001 -- proves extractSenderId
// prefers a phone-based participantPn ONLY for a genuine "@lid"
// participant with a genuinely phone-shaped alternative, and otherwise
// behaves byte-for-byte as before. Uses only obviously synthetic
// JIDs/numbers -- never a real captured identifier.
const GROUP_JID = "120363099999999999@g.us";
const CLASSIC_PHONE_JID = "6289900000001@s.whatsapp.net";
const LID_JID = "99887766554433@lid";
const LID_PHONE_ALTERNATIVE = "6289900000002@s.whatsapp.net";

function groupMessage({ participant, participantPn, text = "/ltsa status 212-P-8A", id = "wamid.LID-TEST-1" }) {
  const key = { remoteJid: GROUP_JID, participant, id, fromMe: false };
  if (participantPn !== undefined) key.participantPn = participantPn;
  return { key, message: { conversation: text }, messageTimestamp: 1735689600 };
}

test("CASE 1 -- classic phone JID: participant used unchanged, no participantPn present", () => {
  const msg = groupMessage({ participant: CLASSIC_PHONE_JID });
  assert.equal(extractSenderId(msg), CLASSIC_PHONE_JID);
});

test("CASE 2 -- LID with a valid phone alternative: participantPn is used", () => {
  const msg = groupMessage({ participant: LID_JID, participantPn: LID_PHONE_ALTERNATIVE });
  assert.equal(extractSenderId(msg), LID_PHONE_ALTERNATIVE);
});

test("CASE 3 -- LID without participantPn: raw LID preserved, never fabricated, fails closed downstream", () => {
  const msg = groupMessage({ participant: LID_JID });
  assert.equal(extractSenderId(msg), LID_JID);
});

test("CASE 4a -- LID with an empty-string participantPn: malformed alternative is not trusted", () => {
  const msg = groupMessage({ participant: LID_JID, participantPn: "" });
  assert.equal(extractSenderId(msg), LID_JID);
});

test("CASE 4b -- LID with a participantPn that isn't phone-shaped: malformed alternative is not trusted", () => {
  const msg = groupMessage({ participant: LID_JID, participantPn: "not-a-real-jid" });
  assert.equal(extractSenderId(msg), LID_JID);
});

test("CASE 4c -- LID with a non-string participantPn: malformed alternative is not trusted", () => {
  const msg = groupMessage({ participant: LID_JID, participantPn: 123456 });
  assert.equal(extractSenderId(msg), LID_JID);
});

test("CASE 5 -- participantPn present on a non-LID participant: classic participant is not unexpectedly replaced", () => {
  const msg = groupMessage({ participant: CLASSIC_PHONE_JID, participantPn: LID_PHONE_ALTERNATIVE });
  assert.equal(extractSenderId(msg), CLASSIC_PHONE_JID);
});

test("end-to-end -- LID + valid participantPn: normalizeGroupMessageEvent's sender_identifier is the phone-based value, ready for the existing hash/authorization pipeline unchanged", () => {
  const msg = groupMessage({ participant: LID_JID, participantPn: LID_PHONE_ALTERNATIVE });
  const event = normalizeGroupMessageEvent(msg);
  assert.ok(event);
  assert.equal(event.sender_identifier, LID_PHONE_ALTERNATIVE);
  assert.equal(event.group_id, GROUP_JID);
  assert.notEqual(event.sender_identifier, event.group_id);
});

test("end-to-end -- classic phone JID is unaffected: normalizeGroupMessageEvent behaves exactly as before this fix", () => {
  const msg = groupMessage({ participant: CLASSIC_PHONE_JID });
  const event = normalizeGroupMessageEvent(msg);
  assert.ok(event);
  assert.equal(event.sender_identifier, CLASSIC_PHONE_JID);
});

test("end-to-end -- LID without a usable alternative still normalizes (fails closed later at the backend hash lookup, not silently dropped here)", () => {
  const msg = groupMessage({ participant: LID_JID });
  const event = normalizeGroupMessageEvent(msg);
  assert.ok(event);
  assert.equal(event.sender_identifier, LID_JID);
});
