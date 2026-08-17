import { statusLabel, statusVariant } from "../utils/engineeringAIRender";

/**
 * Presentational only. Renders the execution_status badge for a given
 * EngineeringAIResponse. No fetch, no Router, no state -- input is the
 * response object (or null/undefined) and nothing else.
 */
export default function EngineeringAIStatus({ response }) {
  return <span className={`status-signal ${statusVariant(response)}`}>{statusLabel(response)}</span>;
}
