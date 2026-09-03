import assert from "node:assert/strict";
import { test } from "node:test";

import { handleIncomingMessage } from "../src/index.js";

const GROUP_JID = "120363012345678901@g.us";
const SENDER_JID = "6281234500002@s.whatsapp.net";

function groupTextMessage({ text, fromMe = false, id = "wamid.TEST-1" }) {
  return {
    key: { remoteJid: GROUP_JID, participant: SENDER_JID, id, fromMe },
    message: { conversation: text },
  };
}

function fakeSock() {
  const sent = [];
  return {
    sent,
    async sendMessage(jid, content) {
      sent.push({ jid, content });
    },
  };
}

// 02 - ordinary chatter never calls the backend and never sends anything
test("ordinary group chatter never calls the backend client and sends nothing", async () => {
  let called = false;
  const client = { async sendGroupMessage() { called = true; return {}; } };
  const sock = fakeSock();
  await handleIncomingMessage(sock, groupTextMessage({ text: "chit chat" }), client);
  assert.equal(called, false);
  assert.deepEqual(sock.sent, []);
});

// 16 - self-message never calls the backend
test("self-sent message never calls the backend client", async () => {
  let called = false;
  const client = { async sendGroupMessage() { called = true; return {}; } };
  const sock = fakeSock();
  await handleIncomingMessage(sock, groupTextMessage({ text: "/ltsa status 212-P-8A", fromMe: true }), client);
  assert.equal(called, false);
});

// 10 - a triggered message forwards exactly one normalized event to the backend
test("a triggered message forwards exactly one call to the backend with the group as sole destination", async () => {
  const calls = [];
  const client = {
    async sendGroupMessage(event) {
      calls.push(event);
      return { status: "ANSWERED", reply: "PUMP OK", ack: "Tunggu sebentar ya..." };
    },
  };
  const sock = fakeSock();
  await handleIncomingMessage(sock, groupTextMessage({ text: "/ltsa status 212-P-8A" }), client);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].group_id, GROUP_JID);
  assert.equal(calls[0].sender_identifier, SENDER_JID);
  // 14 - same-group reply routing: every sendMessage call targets the
  // event's own group id, never anything else.
  assert.ok(sock.sent.every((m) => m.jid === GROUP_JID));
  assert.deepEqual(
    sock.sent.map((m) => m.content.text),
    ["Tunggu sebentar ya...", "PUMP OK"]
  );
});

// failure behavior: backend unreachable -> safe generic reply, no leaked error
test("backend failure yields only the safe generic unavailable reply, to the same group", async () => {
  const client = { async sendGroupMessage() { throw new Error("ECONNREFUSED 10.0.0.5:8000"); } };
  const sock = fakeSock();
  await handleIncomingMessage(sock, groupTextMessage({ text: "/ltsa status 212-P-8A" }), client);
  assert.equal(sock.sent.length, 1);
  assert.equal(sock.sent[0].jid, GROUP_JID);
  assert.equal(sock.sent[0].content.text, "LTSA sedang tidak tersedia. Silakan coba lagi nanti.");
  assert.ok(!sock.sent[0].content.text.includes("ECONNREFUSED"));
});

// unauthorized denial: no ack is sent, only the denial reply
test("unauthorized sender denial sends only the denial text, no acknowledgement", async () => {
  const client = {
    async sendGroupMessage() {
      return { status: "UNAUTHORIZED_SENDER", reply: "Nomor Anda belum memiliki akses LTSA.", ack: null };
    },
  };
  const sock = fakeSock();
  await handleIncomingMessage(sock, groupTextMessage({ text: "/ltsa status 212-P-8A" }), client);
  assert.deepEqual(
    sock.sent.map((m) => m.content.text),
    ["Nomor Anda belum memiliki akses LTSA."]
  );
});
