/**
 * MWO-LTSA-069 -- pure reconnect-policy logic for the TAP LTSA WhatsApp
 * Group Agent transport, split out from index.js exactly as
 * messagePipeline.js already splits message-classification logic from its
 * own Baileys wiring -- so this can be exercised by
 * reconnectPolicy.test.js without a real Baileys socket, network, or auth
 * state on disk.
 *
 * Context (verified against the live production deployment before this
 * was written -- see ENGINEERING/MWO/MWO-LTSA-069-*.md): the previous
 * design exited the process on every "close" event and relied entirely on
 * Docker's `restart: unless-stopped` to reconnect. That is safe but heavy
 * -- 14 full process restarts (fresh login handshake each time) over ~2
 * days in production, all triggered by the SAME transient
 * fetchProps/init-queries timeout, never by an actual logout. This module
 * lets index.js retry transient disconnects in-process first, reserving a
 * full process exit (and Docker's restart) for the cases that actually
 * need it: an unrecoverable auth state, or a transient run that would
 * otherwise retry forever.
 */

// Baileys' own DisconnectReason values (node_modules/@whiskeysockets/
// baileys/lib/Types/index.js) that mean the on-disk auth state itself is
// no longer usable -- reconnecting with the same credentials cannot
// succeed, and retrying only spins:
//   loggedOut (401)  -- the linked device was explicitly unlinked/logged
//                        out from the phone.
//   badSession (500) -- Baileys' own signal that the stored session data
//                        is corrupt/unusable.
// Every other DisconnectReason (connectionClosed 428, connectionLost/
// timedOut 408, connectionReplaced 440, restartRequired 515,
// multideviceMismatch 411, forbidden 403, unavailableService 503) is
// treated as transient -- worth retrying with the SAME auth state, never
// a reason to touch or discard it. An unrecognized/missing status code
// (no Boom attached, or a code Baileys hasn't defined) is also treated as
// transient: absence of evidence that the session is dead is not evidence
// that it is.
const UNRECOVERABLE_STATUS_CODES = new Set([401, 500]);

/**
 * @param {number | undefined} statusCode - update.lastDisconnect?.error?.output?.statusCode
 * @returns {"UNRECOVERABLE" | "TRANSIENT"}
 */
export function classifyDisconnect(statusCode) {
  return UNRECOVERABLE_STATUS_CODES.has(statusCode) ? "UNRECOVERABLE" : "TRANSIENT";
}

export const DEFAULT_MAX_ATTEMPTS = 8;
export const DEFAULT_BASE_DELAY_MS = 2000;
export const DEFAULT_MAX_DELAY_MS = 60000;

/**
 * Bounded exponential backoff with full jitter (AWS-style: a random point
 * in [0, cappedExponentialDelay], not the exponential value itself) --
 * avoids retrying at an exact, predictable moment the far end may still
 * be unhappy with, and avoids any future multi-instance deployment
 * retrying in lockstep.
 *
 * @param {number} attempt - 1-based: the Nth in-process reconnect attempt
 *   since the last successful "open" connection.
 * @returns {number | null} delay in ms, or null once attempt exceeds
 *   maxAttempts -- the caller's own signal to stop retrying in-process and
 *   let Docker's restart policy take over instead (never an infinite
 *   tight retry loop).
 */
export function computeBackoffDelayMs(
  attempt,
  {
    baseDelayMs = DEFAULT_BASE_DELAY_MS,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    maxAttempts = DEFAULT_MAX_ATTEMPTS,
    random = Math.random,
  } = {}
) {
  if (attempt < 1 || attempt > maxAttempts) {
    return null;
  }
  const exponential = baseDelayMs * 2 ** (attempt - 1);
  const capped = Math.min(exponential, maxDelayMs);
  return Math.floor(random() * capped);
}

/**
 * The single decision index.js's "close" handler needs, as one pure,
 * fully testable function -- composes classifyDisconnect() and
 * computeBackoffDelayMs() so the exact end-to-end behavior for a given
 * (statusCode, attempt) pair can be asserted without a real Baileys
 * socket, network, or auth state on disk.
 *
 * @param {number | undefined} statusCode
 * @param {number} attempt - 1-based attempt number for THIS disconnect
 *   (the caller increments its own counter before calling this).
 * @returns
 *   {{ action: "EXIT_UNRECOVERABLE", statusCode: number | undefined }} |
 *   {{ action: "EXIT_ATTEMPTS_EXHAUSTED", statusCode: number | undefined, attempts: number }} |
 *   {{ action: "RECONNECT", statusCode: number | undefined, attempt: number, delayMs: number }}
 */
export function decideOnClose(statusCode, attempt, backoffOptions = {}) {
  if (classifyDisconnect(statusCode) === "UNRECOVERABLE") {
    return { action: "EXIT_UNRECOVERABLE", statusCode };
  }
  const delayMs = computeBackoffDelayMs(attempt, backoffOptions);
  if (delayMs === null) {
    return { action: "EXIT_ATTEMPTS_EXHAUSTED", statusCode, attempts: attempt - 1 };
  }
  return { action: "RECONNECT", statusCode, attempt, delayMs };
}
