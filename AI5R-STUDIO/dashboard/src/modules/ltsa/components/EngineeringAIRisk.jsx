import { formatValue } from "../utils/engineeringAIRender";

/**
 * Presentational only. Renders EngineeringAIResponse.risk. No fetch, no
 * Router, no state.
 */
export default function EngineeringAIRisk({ response }) {
  return (
    <div className="info-row">
      <span className="k">Risk</span>
      <span className="v">{formatValue(response?.risk)}</span>
    </div>
  );
}
