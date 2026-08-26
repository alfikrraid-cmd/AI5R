import { useEffect, useState } from "react";
import { Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import EvidenceAttachments, { EVIDENCE_RECORD_TYPES } from "./EvidenceAttachments";
import { TechnicalOutcomeBadge, WorkflowStatusBadge } from "./WorkflowStatusBadge";

// MWO-LTSA-PM-CM-REVIEW-UI-001 -- displays/edits a real pm_occurrence
// record (a field visit, distinct from the pm_schedule PMOpenDesignView.jsx
// renders -- see pmMapping.js's own header). A new, separate, Card-based
// component (mirroring ConditionMonitoringReadingDetailPanel.jsx's own
// style), NOT an extension of PMOpenDesignView.jsx: that file is confirmed
// fully untracked pre-existing WIP with zero overlap with occurrence data,
// and touching it would risk absorbing unrelated work (Phase 1's own "Do
// not absorb unrelated work").
//
// Same ACTIVITY_OPTIONS subset CreatePMOccurrenceModal.jsx already
// establishes (the backend's `activities` JSONB accepts any subset, this
// is a UI scope choice already made once, reused verbatim here so create
// and edit render/accept the exact same checklist).
const ACTIVITY_OPTIONS = [
  { code: "1", description: "Flushing Line", side: null },
  { code: "4", description: "Quench Line", side: null },
  { code: "19", description: "Strainer", side: null },
  { code: "17", description: "Check Valve DE Side", side: "DE" },
  { code: "18", description: "Check Valve NDE Side", side: "NDE" },
  { code: "6", description: "Reservoir", side: null },
  { code: "8", description: "Cooling Water Cooler", side: null },
];

// Phase 6/9: only DRAFT and RETURNED_FOR_CORRECTION are ever
// client-editable -- matches pm_occurrence_repository.py's own
// _EDITABLE_STATUSES_SQL guard exactly, so the UI's edit gate can never
// promise an edit the backend would reject.
const EDITABLE_STATUSES = new Set(["DRAFT", "RETURNED_FOR_CORRECTION"]);

const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
  boxSizing: "border-box",
};

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

// Phase 12: honest raw actor identifier + timestamp -- no display-name
// resolution exists in this codebase and this MWO forbids building one.
function formatActor(actorId, timestamp) {
  if (!actorId && !timestamp) return "—";
  return timestamp ? `${actorId || "unknown"} · ${timestamp}` : actorId || "unknown";
}

export default function PMOccurrenceDetailPanel({
  occurrence,
  canWrite,
  canAdminReview,
  canTechnicalReview,
  onSaveDraft,
  onSubmit,
  onAdminReturn,
  onTechnicalReview,
  canDelete = false,
  onDelete,
  onOpenPump,
}) {
  const [activities, setActivities] = useState({});
  const [finding, setFinding] = useState("");
  const [preliminaryRecommendation, setPreliminaryRecommendation] = useState("");
  const [remarks, setRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [returnReason, setReturnReason] = useState("");
  const [returning, setReturning] = useState(false);
  const [returnError, setReturnError] = useState(null);

  const [jcComment, setJcComment] = useState("");
  const [jcRecommendation, setJcRecommendation] = useState("");
  const [jcActionPending, setJcActionPending] = useState(null);
  const [jcError, setJcError] = useState(null);

  useEffect(() => {
    if (!occurrence) return;
    const doneMap = {};
    (occurrence.activities ?? []).forEach((entry) => {
      if (entry?.done) doneMap[entry.code] = true;
    });
    setActivities(doneMap);
    setFinding(occurrence.finding ?? "");
    setPreliminaryRecommendation(occurrence.preliminaryRecommendation ?? "");
    setRemarks(occurrence.remarks ?? "");
    setSaveError(null);
    setSubmitError(null);
    setReturnReason("");
    setReturnError(null);
    setJcComment("");
    setJcRecommendation("");
    setJcError(null);
  }, [occurrence?.id]);

  if (!occurrence) {
    return (
      <EmptyState
        title="No PM occurrence selected"
        description="Record or select a PM occurrence to view its details."
      />
    );
  }

  const editable = Boolean(canWrite) && EDITABLE_STATUSES.has(occurrence.workflowStatus);
  const reviewable = occurrence.workflowStatus === "SUBMITTED";

  async function handleDelete() {
    const reason = window.prompt(`Deletion reason for ${occurrence.id}:`);
    if (!reason?.trim()) return;
    if (!window.confirm(`Soft-delete PM Occurrence ${occurrence.id}?`)) return;
    await onDelete?.(occurrence.id, reason.trim());
  }

  function toggleActivity(code) {
    setActivities((current) => ({ ...current, [code]: !current[code] }));
  }

  async function handleSaveDraft() {
    setSaving(true);
    setSaveError(null);
    try {
      const nextActivities = ACTIVITY_OPTIONS.map((option) => ({
        ...option,
        done: Boolean(activities[option.code]),
      }));
      await onSaveDraft?.(occurrence.id, {
        occurrenceDate: occurrence.occurrenceDate,
        activities: nextActivities,
        finding: finding || null,
        preliminaryRecommendation: preliminaryRecommendation || null,
        remarks: remarks || null,
      });
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    if (!window.confirm(`Submit PM Occurrence ${occurrence.id} for review?`)) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onSubmit?.(occurrence.id);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAdminReturn() {
    if (!returnReason.trim()) {
      setReturnError("A return reason is required.");
      return;
    }
    if (!window.confirm(`Return PM Occurrence ${occurrence.id} for correction?`)) return;
    setReturning(true);
    setReturnError(null);
    try {
      await onAdminReturn?.(occurrence.id, returnReason.trim());
      setReturnReason("");
    } catch (err) {
      setReturnError(err.message);
    } finally {
      setReturning(false);
    }
  }

  async function handleTechnicalAction(action) {
    if (action === "RETURN" && !jcComment.trim()) {
      setJcError("A comment is required to return for correction.");
      return;
    }
    const confirmMessage = {
      RETURN: `Return PM Occurrence ${occurrence.id} for correction?`,
      ACKNOWLEDGE: `Acknowledge PM Occurrence ${occurrence.id}? This finalizes the record.`,
      APPROVE: `Technically approve PM Occurrence ${occurrence.id}? This finalizes the record.`,
    }[action];
    if (!window.confirm(confirmMessage)) return;

    setJcActionPending(action);
    setJcError(null);
    try {
      await onTechnicalReview?.(occurrence.id, {
        action,
        comment: jcComment || null,
        recommendation: jcRecommendation || null,
      });
      setJcComment("");
      setJcRecommendation("");
    } catch (err) {
      setJcError(err.message);
    } finally {
      setJcActionPending(null);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm }}>
        <h2 style={{ margin: 0 }}>{occurrence.id}</h2>
        <WorkflowStatusBadge status={occurrence.workflowStatus} />
        <TechnicalOutcomeBadge outcome={occurrence.technicalOutcome} />
      </div>

      {occurrence.workflowStatus === "RETURNED_FOR_CORRECTION" && (
        <Card title="Returned for Correction">
          <p style={{ color: colors.danger, margin: 0 }}>
            Reason: {occurrence.returnReason || occurrence.technicalComment || "No reason recorded."}
          </p>
        </Card>
      )}

      <Card title="Occurrence Summary">
        <Field label="Equipment" value={occurrence.equipmentTag} />
        <Field label="PM Schedule" value={occurrence.pmScheduleCode} />
        <Field label="Occurrence Date" value={occurrence.occurrenceDate ?? "—"} />
      </Card>

      <Card title="Activities">
        {ACTIVITY_OPTIONS.map((option) => (
          <label
            key={option.code}
            style={{ display: "flex", alignItems: "center", gap: spacing.xs, color: colors.text, marginBottom: spacing.xs }}
          >
            <input
              type="checkbox"
              checked={Boolean(activities[option.code])}
              disabled={!editable}
              onChange={() => toggleActivity(option.code)}
            />
            {option.description}
          </label>
        ))}
      </Card>

      <Card title="Finding">
        {editable ? (
          <textarea
            aria-label="Finding"
            style={{ ...fieldStyle, minHeight: 60 }}
            value={finding}
            onChange={(event) => setFinding(event.target.value)}
          />
        ) : (
          <p style={{ color: colors.text, margin: 0 }}>{occurrence.finding || "No finding recorded."}</p>
        )}
      </Card>

      {/* Phase 11 -- Field/Preliminary Recommendation (TAP Engineer) and
          Technical Recommendation (John Crane) are two separate cards,
          never rendered as the same authority. */}
      <Card title="Field Recommendation — TAP Engineer">
        {editable ? (
          <textarea
            aria-label="Field recommendation"
            style={{ ...fieldStyle, minHeight: 60 }}
            value={preliminaryRecommendation}
            onChange={(event) => setPreliminaryRecommendation(event.target.value)}
          />
        ) : (
          <p style={{ color: colors.text, margin: 0 }}>
            {occurrence.preliminaryRecommendation || "No field recommendation recorded."}
          </p>
        )}
      </Card>

      <Card title="Technical Recommendation — John Crane Engineer">
        <p style={{ color: colors.text, margin: 0 }}>
          {occurrence.technicalRecommendation || "No technical recommendation yet."}
        </p>
        {occurrence.technicalComment && (
          <p style={{ color: colors.textMuted, fontSize: 12, marginTop: spacing.xs }}>
            Comment: {occurrence.technicalComment}
          </p>
        )}
      </Card>

      <Card title="Remarks">
        {editable ? (
          <textarea
            aria-label="Remarks"
            style={{ ...fieldStyle, minHeight: 48 }}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
          />
        ) : (
          <p style={{ color: colors.text, margin: 0 }}>{occurrence.remarks || "—"}</p>
        )}
      </Card>

      {/* MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- source-document
          provenance (which workbook/sheet/row this record was imported
          from), distinct from the uploaded-file Evidence card below --
          N/A, never fabricated, for a live-entered record with no
          workbook origin. */}
      <Card title="Source">
        <Field label="Source Workbook" value={occurrence.sourceWorkbookName ?? "N/A"} />
        <Field label="Source Sheet" value={occurrence.sourceSheetName ?? "N/A"} />
        <Field label="Source Row" value={occurrence.sourceRowNumber ?? "N/A"} />
      </Card>

      <Card title="Evidence">
        <EvidenceAttachments
          recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE}
          recordCode={occurrence.id}
          canUpload={editable}
        />
      </Card>

      <Card title="Attribution">
        <Field label="Created" value={formatActor(occurrence.createdBy, occurrence.createdAt)} />
        <Field label="Updated" value={formatActor(occurrence.updatedBy, occurrence.updatedAt)} />
        <Field label="Submitted" value={formatActor(occurrence.submittedBy, occurrence.submittedAt)} />
        <Field label="Admin Review" value={formatActor(occurrence.reviewedBy, occurrence.reviewedAt)} />
        <Field
          label="Technical Review"
          value={formatActor(occurrence.technicalReviewedBy, occurrence.technicalReviewedAt)}
        />
      </Card>

      {editable && (
        <Card title="Actions">
          {saveError && (
            <p role="alert" style={{ color: colors.danger }}>
              {saveError}
            </p>
          )}
          {submitError && (
            <p role="alert" style={{ color: colors.danger }}>
              {submitError}
            </p>
          )}
          <div style={{ display: "flex", gap: spacing.sm }}>
            <Button onClick={handleSaveDraft} disabled={saving || submitting}>
              {saving ? "Saving..." : "Save Draft"}
            </Button>
            <Button onClick={handleSubmit} disabled={saving || submitting}>
              {submitting ? "Submitting..." : "Submit"}
            </Button>
          </div>
        </Card>
      )}

      {reviewable && canAdminReview && (
        <Card title="TAP Admin Review">
          {returnError && (
            <p role="alert" style={{ color: colors.danger }}>
              {returnError}
            </p>
          )}
          <textarea
            aria-label="Return reason"
            style={{ ...fieldStyle, minHeight: 48 }}
            placeholder="Reason for returning this record for correction..."
            value={returnReason}
            onChange={(event) => setReturnReason(event.target.value)}
            disabled={returning}
          />
          <div style={{ marginTop: spacing.sm }}>
            <Button onClick={handleAdminReturn} disabled={returning}>
              {returning ? "Returning..." : "Return for Correction"}
            </Button>
          </div>
        </Card>
      )}

      {reviewable && canTechnicalReview && (
        <Card title="John Crane Technical Review">
          {jcError && (
            <p role="alert" style={{ color: colors.danger }}>
              {jcError}
            </p>
          )}
          <textarea
            aria-label="Technical comment"
            style={{ ...fieldStyle, minHeight: 48, marginBottom: spacing.sm }}
            placeholder="Technical comment..."
            value={jcComment}
            onChange={(event) => setJcComment(event.target.value)}
            disabled={Boolean(jcActionPending)}
          />
          <textarea
            aria-label="Technical recommendation"
            style={{ ...fieldStyle, minHeight: 48 }}
            placeholder="Technical recommendation (for Acknowledge / Technically Approve)..."
            value={jcRecommendation}
            onChange={(event) => setJcRecommendation(event.target.value)}
            disabled={Boolean(jcActionPending)}
          />
          <div style={{ display: "flex", gap: spacing.sm, marginTop: spacing.sm }}>
            <Button onClick={() => handleTechnicalAction("RETURN")} disabled={Boolean(jcActionPending)}>
              {jcActionPending === "RETURN" ? "Returning..." : "Return for Correction"}
            </Button>
            <Button onClick={() => handleTechnicalAction("ACKNOWLEDGE")} disabled={Boolean(jcActionPending)}>
              {jcActionPending === "ACKNOWLEDGE" ? "Acknowledging..." : "Acknowledge"}
            </Button>
            <Button onClick={() => handleTechnicalAction("APPROVE")} disabled={Boolean(jcActionPending)}>
              {jcActionPending === "APPROVE" ? "Approving..." : "Technically Approve"}
            </Button>
          </div>
        </Card>
      )}

      {reviewable && !canAdminReview && !canTechnicalReview && (
        <Card title="Status">
          <p style={{ color: colors.textMuted, margin: 0 }}>
            Submitted and awaiting review. This record is read-only until reviewed.
          </p>
        </Card>
      )}

      {occurrence.equipmentTag && (
        <Card title="Quick Actions">
          <Button onClick={() => onOpenPump?.(occurrence.equipmentTag)}>Open Pump</Button>
        </Card>
      )}
      {canDelete && <Card title="Danger Zone"><Button onClick={handleDelete}>Soft Delete</Button></Card>}
    </div>
  );
}
