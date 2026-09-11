import test from "node:test";
import assert from "node:assert/strict";

import {
  classifyDisconnect,
  computeBackoffDelayMs,
  decideOnClose,
  DEFAULT_MAX_ATTEMPTS,
  DEFAULT_BASE_DELAY_MS,
  DEFAULT_MAX_DELAY_MS,
} from "../src/reconnectPolicy.js";

test("loggedOut (401) is classified UNRECOVERABLE", () => {
  assert.equal(classifyDisconnect(401), "UNRECOVERABLE");
});

test("badSession (500) is classified UNRECOVERABLE", () => {
  assert.equal(classifyDisconnect(500), "UNRECOVERABLE");
});

test("connectionClosed (428) is classified TRANSIENT", () => {
  assert.equal(classifyDisconnect(428), "TRANSIENT");
});

test("connectionLost/timedOut (408) is classified TRANSIENT -- this is the exact code behind the observed production crash loop", () => {
  assert.equal(classifyDisconnect(408), "TRANSIENT");
});

test("connectionReplaced (440) is classified TRANSIENT", () => {
  assert.equal(classifyDisconnect(440), "TRANSIENT");
});

test("restartRequired (515) is classified TRANSIENT", () => {
  assert.equal(classifyDisconnect(515), "TRANSIENT");
});

test("an unknown/undefined status code is classified TRANSIENT, never UNRECOVERABLE -- absence of evidence the session is dead is not evidence that it is", () => {
  assert.equal(classifyDisconnect(undefined), "TRANSIENT");
  assert.equal(classifyDisconnect(999), "TRANSIENT");
});

test("computeBackoffDelayMs: attempt 1 never exceeds baseDelayMs", () => {
  for (let i = 0; i < 50; i += 1) {
    const delay = computeBackoffDelayMs(1, { random: () => i / 50 });
    assert.ok(delay >= 0 && delay <= DEFAULT_BASE_DELAY_MS);
  }
});

test("computeBackoffDelayMs: delay grows with attempt number (upper bound doubles each time, until the cap)", () => {
  const upperBoundAt = (attempt) => computeBackoffDelayMs(attempt, { random: () => 1 - Number.EPSILON });
  const delay1 = upperBoundAt(1);
  const delay2 = upperBoundAt(2);
  const delay3 = upperBoundAt(3);
  assert.ok(delay2 > delay1);
  assert.ok(delay3 > delay2);
});

test("computeBackoffDelayMs: never exceeds maxDelayMs regardless of attempt number", () => {
  const delay = computeBackoffDelayMs(DEFAULT_MAX_ATTEMPTS, { random: () => 1 - Number.EPSILON });
  assert.ok(delay <= DEFAULT_MAX_DELAY_MS);
});

test("computeBackoffDelayMs: returns null once attempt exceeds maxAttempts -- the bounded-retry exit signal", () => {
  assert.equal(computeBackoffDelayMs(DEFAULT_MAX_ATTEMPTS + 1), null);
});

test("computeBackoffDelayMs: attempt 0 or negative is invalid and returns null, never a negative/garbage delay", () => {
  assert.equal(computeBackoffDelayMs(0), null);
  assert.equal(computeBackoffDelayMs(-1), null);
});

test("computeBackoffDelayMs: custom bounds are honored (never falls back to the module defaults silently)", () => {
  const delay = computeBackoffDelayMs(1, { baseDelayMs: 100, maxDelayMs: 200, maxAttempts: 2, random: () => 1 - Number.EPSILON });
  assert.ok(delay <= 100);
  assert.equal(computeBackoffDelayMs(3, { baseDelayMs: 100, maxDelayMs: 200, maxAttempts: 2 }), null);
});

// -- decideOnClose: the exact end-to-end decision index.js's own "close"
// handler delegates to, covering the three scenarios MWO-LTSA-069 calls
// out by name: transient reconnect, logged-out (unrecoverable) behavior,
// and bounded-retry exhaustion.

test("decideOnClose: a transient disconnect (408, the exact code behind the observed production crash loop) reconnects with a bounded delay", () => {
  const decision = decideOnClose(408, 1, { random: () => 0.5 });
  assert.equal(decision.action, "RECONNECT");
  assert.equal(decision.attempt, 1);
  assert.ok(decision.delayMs >= 0 && decision.delayMs <= DEFAULT_BASE_DELAY_MS);
});

test("decideOnClose: loggedOut (401) never reconnects, regardless of attempt number", () => {
  const decision = decideOnClose(401, 1);
  assert.equal(decision.action, "EXIT_UNRECOVERABLE");
  assert.equal(decision.statusCode, 401);
});

test("decideOnClose: badSession (500) never reconnects", () => {
  const decision = decideOnClose(500, 1);
  assert.equal(decision.action, "EXIT_UNRECOVERABLE");
});

test("decideOnClose: exhausting maxAttempts on repeated transient disconnects yields EXIT_ATTEMPTS_EXHAUSTED, never an unbounded loop", () => {
  const decision = decideOnClose(408, DEFAULT_MAX_ATTEMPTS + 1);
  assert.equal(decision.action, "EXIT_ATTEMPTS_EXHAUSTED");
  assert.equal(decision.attempts, DEFAULT_MAX_ATTEMPTS);
});

test("decideOnClose: an unrecoverable disconnect exits even on the very first attempt -- it never spends any retry budget first", () => {
  const decision = decideOnClose(401, 1);
  assert.equal(decision.action, "EXIT_UNRECOVERABLE");
});
