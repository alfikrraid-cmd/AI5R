// Canonical LTSA Engineering AI UI package. Every LTSA workspace SHALL
// import Engineering AI presentation components and render helpers from
// here -- never from an individual component file directly, and never by
// re-implementing rendering logic in a workspace (see
// FailureAnalysisWorkspace.jsx, the Golden Reference, and
// engineeringAIRender.js's own header comment).
//
// Packaging only: this barrel re-exports the existing components and
// helpers unchanged. No component was renamed, moved, or modified to
// produce this file, following the same "export { default as X } from
// ..." convention already established by src/design-system/index.js.

export { default as EngineeringAIStatus } from "../EngineeringAIStatus";
export { default as EngineeringAISummary } from "../EngineeringAISummary";
export { default as EngineeringAIProviderInfo } from "../EngineeringAIProviderInfo";
export { default as EngineeringAIConfidence } from "../EngineeringAIConfidence";
export { default as EngineeringAIRisk } from "../EngineeringAIRisk";
export { default as EngineeringAIRemainingLife } from "../EngineeringAIRemainingLife";
export { default as EngineeringAIFindings } from "../EngineeringAIFindings";
export { default as EngineeringAIEvidence } from "../EngineeringAIEvidence";
export { default as EngineeringAIRecommendation } from "../EngineeringAIRecommendation";
export { default as EngineeringAISourceReferences } from "../EngineeringAISourceReferences";

export {
  renderAIItem,
  formatConfidence,
  formatLatency,
  formatValue,
  statusVariant,
  statusLabel,
} from "../../utils/engineeringAIRender";
