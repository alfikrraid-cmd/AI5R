/**
 * LTSA_CM_UI_REMEDIATION_R1A -- canonical mechanical-seal leak semantics for
 * the dashboard. Mirrors CORE-SERVICES/API/cm_condition_evaluator.py
 * (canonical_leak_state / is_active_leak): DE and NDE are independent
 * tri-states, any `true` dominates, `null` is never coerced to `false`, and a
 * single `false` side with the other side unrecorded is PARTIAL, not NO_LEAK.
 *
 * Shared helper only: consumers migrate in R1B/R1C, the prominent alert
 * component is R1D.
 */

export const LEAK_STATES = Object.freeze({
  LEAK_DE_AND_NDE: "LEAK_DE_AND_NDE",
  LEAK_DE: "LEAK_DE",
  LEAK_NDE: "LEAK_NDE",
  NO_LEAK: "NO_LEAK",
  NO_LEAK_DE_ONLY: "NO_LEAK_DE_ONLY",
  NO_LEAK_NDE_ONLY: "NO_LEAK_NDE_ONLY",
  UNKNOWN: "UNKNOWN",
});

const ACTIVE_LEAK_STATES = new Set([LEAK_STATES.LEAK_DE_AND_NDE, LEAK_STATES.LEAK_DE, LEAK_STATES.LEAK_NDE]);

/** Only the literal booleans count as recorded; anything else is unknown. */
export function leakState(de, nde) {
  const deLeak = de === true;
  const ndeLeak = nde === true;
  if (deLeak && ndeLeak) return LEAK_STATES.LEAK_DE_AND_NDE;
  if (deLeak) return LEAK_STATES.LEAK_DE;
  if (ndeLeak) return LEAK_STATES.LEAK_NDE;
  const deClear = de === false;
  const ndeClear = nde === false;
  if (deClear && ndeClear) return LEAK_STATES.NO_LEAK;
  if (deClear) return LEAK_STATES.NO_LEAK_DE_ONLY;
  if (ndeClear) return LEAK_STATES.NO_LEAK_NDE_ONLY;
  return LEAK_STATES.UNKNOWN;
}

export function isActiveLeak(state) {
  return ACTIVE_LEAK_STATES.has(state);
}

// tone: "critical" (leak), "normal" (confirmed no leak), "neutral" (partial or
// unknown -- never the success/normal tone).
const PRESENTATION = Object.freeze({
  [LEAK_STATES.LEAK_DE_AND_NDE]: { label: "Leak Detected — DE & NDE", tone: "critical", side: "DE_AND_NDE", isLeak: true, isComplete: true },
  [LEAK_STATES.LEAK_DE]: { label: "Leak Detected — DE", tone: "critical", side: "DE", isLeak: true, isComplete: false },
  [LEAK_STATES.LEAK_NDE]: { label: "Leak Detected — NDE", tone: "critical", side: "NDE", isLeak: true, isComplete: false },
  [LEAK_STATES.NO_LEAK]: { label: "No Leak", tone: "normal", side: "DE_AND_NDE", isLeak: false, isComplete: true },
  [LEAK_STATES.NO_LEAK_DE_ONLY]: { label: "No Leak — DE · NDE Not Recorded", tone: "neutral", side: "DE", isLeak: false, isComplete: false },
  [LEAK_STATES.NO_LEAK_NDE_ONLY]: { label: "No Leak — NDE · DE Not Recorded", tone: "neutral", side: "NDE", isLeak: false, isComplete: false },
  [LEAK_STATES.UNKNOWN]: { label: "Not Recorded", tone: "neutral", side: null, isLeak: false, isComplete: false },
});

/**
 * Presentation for a canonical state. `isComplete` for leak states means both
 * sides were recorded; pass (de, nde) to leakPresentationFor() to get it
 * exactly for a reading.
 */
export function leakPresentation(state) {
  const presentation = PRESENTATION[state] ?? PRESENTATION[LEAK_STATES.UNKNOWN];
  return { state: PRESENTATION[state] ? state : LEAK_STATES.UNKNOWN, ...presentation };
}

export function leakPresentationFor(de, nde) {
  const state = leakState(de, nde);
  const recorded = (value) => value === true || value === false;
  return { ...leakPresentation(state), isComplete: recorded(de) && recorded(nde) };
}

// LTSA_CM_UI_REMEDIATION_R1C -- presentation helpers shared by occurrence views.

const BADGE_VARIANT = Object.freeze({ critical: "danger", normal: "success", neutral: "neutral" });

/** design-system Badge variant for a presentation tone; unknown tones are neutral. */
export function leakBadgeVariant(tone) {
  return BADGE_VARIANT[tone] ?? "neutral";
}

export const LEAK_BUCKETS = Object.freeze({ LEAK: "LEAK", NORMAL: "NORMAL", PARTIAL: "PARTIAL", UNKNOWN: "UNKNOWN" });

/**
 * Filter/classification bucket for an occurrence state: only a confirmed
 * NO_LEAK is NORMAL; one-sided records are PARTIAL; nothing recorded is UNKNOWN.
 */
export function leakBucket(state) {
  if (isActiveLeak(state)) return LEAK_BUCKETS.LEAK;
  if (state === LEAK_STATES.NO_LEAK) return LEAK_BUCKETS.NORMAL;
  if (state === LEAK_STATES.NO_LEAK_DE_ONLY || state === LEAK_STATES.NO_LEAK_NDE_ONLY) return LEAK_BUCKETS.PARTIAL;
  return LEAK_BUCKETS.UNKNOWN;
}
