import { Badge } from "../../../design-system";

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 5 -- shared status rendering for
// both PM Occurrence and Condition Monitoring Reading detail views.
// Renders ONLY the real backend workflow_status vocabulary
// (pm_cm_workflow_service.py: DRAFT / SUBMITTED / RETURNED_FOR_CORRECTION
// / FINALIZED) and technical_outcome (ACKNOWLEDGED / TECHNICALLY_APPROVED)
// -- no frontend-only state is invented; an unrecognized value still
// renders honestly (raw text, neutral color) rather than being hidden.
const STATUS_VARIANT = {
  DRAFT: "purple",
  SUBMITTED: "warning",
  RETURNED_FOR_CORRECTION: "danger",
  FINALIZED: "success",
};

const OUTCOME_VARIANT = {
  ACKNOWLEDGED: "info",
  TECHNICALLY_APPROVED: "success",
};

const OUTCOME_LABEL = {
  ACKNOWLEDGED: "Acknowledged",
  TECHNICALLY_APPROVED: "Technically Approved",
};

export function WorkflowStatusBadge({ status }) {
  if (!status) {
    return <Badge variant="purple">UNKNOWN</Badge>;
  }
  return <Badge variant={STATUS_VARIANT[status] ?? "purple"}>{status.replace(/_/g, " ")}</Badge>;
}

// Workflow status and technical outcome are different concepts (Phase 5)
// -- this is a SEPARATE badge, never merged into WorkflowStatusBadge's own
// label, and renders nothing at all when no technical outcome exists yet
// (never fabricates a placeholder outcome).
export function TechnicalOutcomeBadge({ outcome }) {
  if (!outcome) {
    return null;
  }
  return <Badge variant={OUTCOME_VARIANT[outcome] ?? "purple"}>{OUTCOME_LABEL[outcome] ?? outcome}</Badge>;
}
