/**
 * Presentational only. Renders EngineeringAIResponse.summary, or
 * response.error in its place when execution failed -- the same "error
 * instead of summary" slot the Golden Reference (FailureAnalysisWorkspace)
 * already used. No fetch, no Router, no state.
 */
export default function EngineeringAISummary({ response }) {
  const text = response?.error || response?.summary || "Unavailable";
  return <p className="v">{text}</p>;
}
