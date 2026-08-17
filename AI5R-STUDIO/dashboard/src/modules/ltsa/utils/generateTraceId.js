/**
 * Shared trace_id generator for Engineering AI requests. The caller (a
 * workspace) owns trace generation -- the backend never generates one, it
 * only echoes the same trace_id back unchanged (EngineeringAIOrchestrator).
 *
 * Extracted here, identical in behavior to the inline generateTraceId()
 * already in FailureAnalysisWorkspace.jsx, so Pump Workspace (and any
 * future workspace) reuses one implementation instead of duplicating it.
 * FailureAnalysisWorkspace.jsx keeps its own local copy unchanged because
 * it is frozen/read-only for this MWO (Golden Reference) -- not modified
 * here, per "Reuse > Extend > Create" applied to new consumers going
 * forward rather than retrofitting a frozen file.
 */
export default function generateTraceId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `trace-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
