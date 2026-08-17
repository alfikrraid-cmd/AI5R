import { formatLatency } from "../utils/engineeringAIRender";

/**
 * Presentational only. Renders Provider, Latency, and Trace ID as the
 * three .info-row entries the Golden Reference (FailureAnalysisWorkspace)
 * already used for this metadata group. No fetch, no Router, no state.
 */
export default function EngineeringAIProviderInfo({ response }) {
  return (
    <>
      <div className="info-row">
        <span className="k">Provider</span>
        <span className="v">{response?.provider ?? "Unavailable"}</span>
      </div>
      <div className="info-row">
        <span className="k">Latency</span>
        <span className="v">{formatLatency(response?.latency)}</span>
      </div>
      <div className="info-row">
        <span className="k">Trace ID</span>
        <span className="v">{response?.trace_id ?? "Unavailable"}</span>
      </div>
    </>
  );
}
