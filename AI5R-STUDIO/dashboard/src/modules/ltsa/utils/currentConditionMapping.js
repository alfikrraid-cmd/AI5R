import { isActiveLeak, LEAK_STATES } from "./leakSemantics";

/**
 * LTSA_CM_UI_REMEDIATION_R1B -- maps the backend's canonical Current Condition
 * (cm_summary.current_leak_condition, from cm_condition_evaluator.
 * current_leak_condition) for dashboard consumers. The backend already chose
 * the latest valid occurrence; this never re-sorts or re-filters readings.
 *
 * workflowStatus is passed through unchanged (DRAFT is not FINALIZED); no UI
 * badge is derived from it here -- deferred until
 * LTSA_HISTORICAL_CM_WORKFLOW_STATUS_REMEDIATION.
 */
export function mapCurrentCondition(raw) {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const leakState = Object.values(LEAK_STATES).includes(raw.state) ? raw.state : LEAK_STATES.UNKNOWN;
  return {
    readingCode: raw.reading_code ?? null,
    readingDate: raw.reading_date ?? null,
    workflowStatus: raw.workflow_status ?? null,
    leakState,
    // The backend's own boolean, cross-checked against the state so an
    // inconsistent payload can never show an active leak for a non-leak state.
    activeLeak: raw.active === true && isActiveLeak(leakState),
    leakDe: raw.de === true || raw.de === false ? raw.de : null,
    leakNde: raw.nde === true || raw.nde === false ? raw.nde : null,
    completeness: raw.completeness ?? null,
    hasCurrentReading: raw.has_current_reading === true,
  };
}
