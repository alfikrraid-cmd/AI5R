import assert from "node:assert/strict";
import { test } from "node:test";

import {
  extractGroupId,
  extractLtsaTrigger,
  extractSenderId,
  extractText,
  isFromSelf,
  isGroupMessage,
  normalizeGroupMessageEvent,
} from "../src/messagePipeline.js";

const GROUP_JID = "120363012345678901@g.us";
const PERSONAL_JID = "6281234500001@s.whatsapp.net";
const SENDER_JID = "6281234500002@s.whatsapp.net";

function groupTextMessage({ text, fromMe = false, id = "wamid.TEST-1", participant = SENDER_JID }) {
  return {
    key: { remoteJid: GROUP_JID, participant, id, fromMe },
    message: { conversation: text },
    messageTimestamp: 1735689600,
  };
}

function personalTextMessage({ text, fromMe = false, id = "wamid.TEST-2" }) {
  return {
    key: { remoteJid: PERSONAL_JID, id, fromMe },
    message: { conversation: text },
    messageTimestamp: 1735689600,
  };
}

// 01 - personal message -> not a group message
test("01 personal message is not classified as a group message", () => {
  const msg = personalTextMessage({ text: "/ltsa status 212-P-8A" });
  assert.equal(isGroupMessage(msg), false);
  assert.equal(normalizeGroupMessageEvent(msg), null);
});

// 02 - ordinary group chatter -> structurally normalizable, but trigger extraction returns null
test("02 ordinary group chatter yields no trigger", () => {
  const msg = groupTextMessage({ text: "mantap gan pompa nya jalan terus" });
  const event = normalizeGroupMessageEvent(msg);
  assert.ok(event);
  assert.equal(extractLtsaTrigger(event.text), null);
});

// 03 - /ltsa not first token -> no trigger
test("03 trigger not as first token is ignored", () => {
  assert.equal(extractLtsaTrigger("tolong /ltsa status 212-P-8A"), null);
  assert.equal(extractLtsaTrigger("status 212-P-8A"), null);
  assert.equal(extractLtsaTrigger("@agent status 212-P-8A"), null);
});

// 04 - case-insensitive trigger
test("04 trigger is case-insensitive and tolerates leading whitespace", () => {
  assert.equal(extractLtsaTrigger("/ltsa status 212-P-8A"), "status 212-P-8A");
  assert.equal(extractLtsaTrigger("/LTSA status 212-P-8A"), "status 212-P-8A");
  assert.equal(extractLtsaTrigger("   /ltsa kapan terakhir PM 212-P-8A?"), "kapan terakhir PM 212-P-8A?");
});

// 05 - trigger with no question
test("05 trigger with no question yields an empty (not null) question", () => {
  assert.equal(extractLtsaTrigger("/ltsa"), "");
  assert.equal(extractLtsaTrigger("/ltsa   "), "");
});

// 16 - self-message ignored
test("16 self-sent message is never normalized into an event", () => {
  const msg = groupTextMessage({ text: "/ltsa status 212-P-8A", fromMe: true });
  assert.equal(isFromSelf(msg), true);
  assert.equal(normalizeGroupMessageEvent(msg), null);
});

// group id vs sender id must never be conflated
test("group id and sender id are read from distinct fields and are never equal by construction", () => {
  const msg = groupTextMessage({ text: "/ltsa status 212-P-8A" });
  assert.equal(extractGroupId(msg), GROUP_JID);
  assert.equal(extractSenderId(msg), SENDER_JID);
  assert.notEqual(extractGroupId(msg), extractSenderId(msg));
});

// malformed: group message missing participant -> null sender, event dropped
test("19 group message missing participant is treated as malformed, not misattributed to the group", () => {
  const msg = {
    key: { remoteJid: GROUP_JID, id: "wamid.NOPARTICIPANT", fromMe: false },
    message: { conversation: "/ltsa status 212-P-8A" },
  };
  assert.equal(extractSenderId(msg), null);
  assert.equal(normalizeGroupMessageEvent(msg), null);
});

test("extendedTextMessage body is read the same as a plain conversation body", () => {
  const msg = {
    key: { remoteJid: GROUP_JID, participant: SENDER_JID, id: "wamid.EXT-1", fromMe: false },
    message: { extendedTextMessage: { text: "/ltsa status 212-P-8A" } },
  };
  assert.equal(extractText(msg), "/ltsa status 212-P-8A");
  const event = normalizeGroupMessageEvent(msg);
  assert.equal(event.text, "/ltsa status 212-P-8A");
});
