import { formatConfidence } from "../utils/engineeringAIRender";

/**
 * Presentational only. Renders EngineeringAIResponse.confidence as a
 * rounded percentage (plain text, per WORK_ORDER_WORKSPACE's
 * DESIGN-HANDOFF: "do not turn a percentage into a gauge/ring/chart").
 * No fetch, no Router, no state.
 */
export default function EngineeringAIConfidence({ response }) {
  return (
    <div className="info-row">
      <span className="k">Confidence</span>
      <span className="v">{formatConfidence(response?.confidence)}</span>
    </div>
  );
}
