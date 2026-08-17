import { formatValue } from "../utils/engineeringAIRender";

/**
 * Presentational only. Renders EngineeringAIResponse.remaining_life. No
 * fetch, no Router, no state.
 */
export default function EngineeringAIRemainingLife({ response }) {
  return (
    <div className="info-row">
      <span className="k">Remaining Life</span>
      <span className="v">{formatValue(response?.remaining_life)}</span>
    </div>
  );
}
