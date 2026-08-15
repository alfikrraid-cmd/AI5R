/**
 * MWO-LTSA-078 -- Knowledge Review Workspace, pure derivation helpers.
 * Frontend only, no backend call changes: this file performs no fetch and
 * defines no new entity mapping -- Pump/Seal/Installation/Document rows
 * are mapped by the EXISTING pumpMapping.js/sealMapping.js/
 * installationMapping.js/documentMapping.js (the same reuse
 * import_validator.py's own header comment explicitly names: "the four
 * entity shapes read here ... are exactly the snake_case 'Raw Backend'
 * shapes pumpMapping.js/sealMapping.js/installationMapping.js/
 * documentMapping.js already map from"). Only the few derivations with no
 * existing home live here.
 */

/**
 * "Drawing" is not a separate list in the backend's ImportPackage/
 * ValidatedImportPackage (CORE-SERVICES/API/import_validator.py) -- it is
 * document_type === "DRAWING" within `documents`, the exact same
 * real-data relationship LTSAKnowledgeService._build_drawings() and
 * DrawingWorkspace's own drawingMapping.js already establish. Filtering
 * here, rather than fabricating a second Drawing list, is the one
 * faithful way to give this Knowledge Package viewer its own Drawing
 * section without inventing backend data that doesn't exist.
 */
export function deriveDrawingRecords(documents) {
  return documents.filter((record) => record.document_type === "DRAWING");
}

// Reuses the exact "ok" / "pending" / "low" stock-flag vocabulary
// PumpOpenDesignView.jsx's own Compatible Seals RefGroup already
// established (LTSAOpenDesign.css already styles all three) -- not a new
// color/flag system invented for Validation.
export function severityToFlag(severity) {
  if (severity === "ERROR") return "low";
  if (severity === "WARNING") return "pending";
  return "ok";
}

export function severityToFlagLabel(severity) {
  if (severity === "ERROR") return "Error";
  if (severity === "WARNING") return "Warning";
  return "Valid";
}

/**
 * Human-readable relationship label, e.g. "installation 'INSTL-001' -> pump
 * '211-P-1A' (resolved)" -- built entirely from the real
 * ImportRelationship fields (from_entity_type/from_entity_id/field/
 * to_entity_type/to_entity_id/resolved), never generated free text beyond
 * joining those real values with fixed, disclosed punctuation.
 */
export function describeRelationship(relationship) {
  const arrow = relationship.resolved ? "→" : "⇢";
  return `${relationship.from_entity_type} '${relationship.from_entity_id}' ${arrow} ${relationship.to_entity_type} '${relationship.to_entity_id}' (via ${relationship.field})`;
}
