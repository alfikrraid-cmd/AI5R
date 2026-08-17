/**
 * Shared, presentational-only rendering helpers for EngineeringAIResponse
 * fields (MWO extracting Engineering AI UI from FailureAnalysisWorkspace,
 * the Golden Reference). Pure functions only -- no fetch, no state, no
 * business logic. Every EngineeringAI* component imports from here instead
 * of re-deriving these formats, per "No duplicated rendering".
 */

export function renderAIItem(item, index) {
  const text =
    typeof item === "string"
      ? item
      : item?.text ?? item?.summary ?? item?.description ?? item?.reference ?? JSON.stringify(item);
  return { key: index, text };
}

export function formatConfidence(value) {
  return value === null || value === undefined ? "Unavailable" : `${Math.round(value * 100)}%`;
}

export function formatLatency(value) {
  return value === null || value === undefined ? "Unavailable" : `${Math.round(value * 1000)} ms`;
}

export function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Unavailable";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

// Mirrors the CSS's real .status-signal variants (MaintenanceHistory.css):
// normal, attention, critical, unavailable, neutral -- no new variant names.
export function statusVariant(response) {
  if (!response) return "unavailable";
  if (response.error) return "critical";
  return response.execution_status === "SUCCESS" ? "normal" : "attention";
}

export function statusLabel(response) {
  if (!response) return "Unavailable";
  if (response.error) return "Error";
  return response.execution_status ?? "Unavailable";
}
