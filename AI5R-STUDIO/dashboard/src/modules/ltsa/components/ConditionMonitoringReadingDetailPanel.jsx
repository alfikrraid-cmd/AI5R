import { useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import EvidenceAttachments, { EVIDENCE_RECORD_TYPES } from "./EvidenceAttachments";
import { TechnicalOutcomeBadge, WorkflowStatusBadge } from "./WorkflowStatusBadge";
import {
  MEASUREMENT_PAIR_FIELDS,
  MEASUREMENT_SINGLE_FIELDS,
  LEAK_FIELD,
  buildMeasurementsPayload as buildManagedMeasurementsPayload,
  measurementFormValuesFromReading,
} from "../utils/conditionMonitoringMeasurementFields";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

function tempValue(value) {
  return value != null ? `${value} °C` : "—";
}

function pressureValue(value) {
  return value != null ? `${value} bar` : "—";
}

function vibrationValue(value) {
  return value != null ? `${value} mm/s` : "—";
}

function leakLabel(value) {
  if (value === true) return "Leak Detected";
  if (value === false) return "No Leak";
  return "Not Recorded";
}

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 12: honest raw actor identifier +
// timestamp -- no display-name resolution exists in this codebase and
// this MWO forbids building one.
function formatActor(actorId, timestamp) {
  if (!actorId && !timestamp) return "—";
  return timestamp ? `${actorId || "unknown"} · ${timestamp}` : actorId || "unknown";
}

const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
  boxSizing: "border-box",
};

const LEAK_OPTIONS = [
  { value: "", label: "Not Recorded" },
  { value: "false", label: "No Leak" },
  { value: "true", label: "Leak Detected" },
];

const OPERATING_STATE_OPTIONS = ["Running", "Standby", "Repair"];

// condition_monitoring_reading_repository.py's update_draft SETs every
// one of _MEASUREMENT_COLUMNS from the `measurements` object it is given
// -- there is no partial-column PATCH. As of
// MWO-LTSA-PM-CMON-FOUNDATION-CLEANUP-001, conditionMonitoringMeasurement
// Fields.js manages the COMPLETE _MEASUREMENT_COLUMNS set (the migration-
// 014 fields plus the golden-evidence-backed legacy WO-CMON-001 fields --
// flushing/quench/flushing-in-out/cooling-water-in-out/water-jacket,
// ADR-CONDITION-MONITORING-001), so no separate passthrough is needed
// anymore -- buildManagedMeasurementsPayload() alone is always complete.

const EDITABLE_STATUSES = new Set(["DRAFT", "RETURNED_FOR_CORRECTION"]);

// One shared row renderer for a DE/NDE measurement pair -- read-only
// combined display (existing convention) when not editable, two
// separately-labeled inputs (never collapsed) when editable. Local to
// this panel, not a new CM form.
function MeasurementPairRow({ field, editable, values, onChange, formatValue }) {
  if (!editable) {
    return (
      <Field
        label={`${field.group} (${field.unit})`}
        value={`${formatValue(values[field.deKey])} / ${formatValue(values[field.ndeKey])}`}
      />
    );
  }

  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>
        {field.group} ({field.unit})
      </div>
      <div style={{ display: "flex", gap: spacing.sm }}>
        <input
          aria-label={`${field.group} DE`}
          type="number"
          step="any"
          style={fieldStyle}
          value={values[field.deKey]}
          onChange={(event) => onChange(field.deKey, event.target.value)}
        />
        <input
          aria-label={`${field.group} NDE`}
          type="number"
          step="any"
          style={fieldStyle}
          value={values[field.ndeKey]}
          onChange={(event) => onChange(field.ndeKey, event.target.value)}
        />
      </div>
    </div>
  );
}

function MeasurementSingleRow({ field, editable, values, onChange, formatValue }) {
  if (!editable) {
    return <Field label={`${field.label} (${field.unit})`} value={formatValue(values[field.key])} />;
  }

  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>
        {field.label} ({field.unit})
      </div>
      <input
        aria-label={field.label}
        type="number"
        step="any"
        style={fieldStyle}
        value={values[field.key]}
        onChange={(event) => onChange(field.key, event.target.value)}
      />
    </div>
  );
}

export default function ConditionMonitoringReadingDetailPanel({
  reading,
  onViewAsset360,
  onViewSchedule,
  canWrite,
  canAdminReview,
  canTechnicalReview,
  onSaveDraft,
  onSubmit,
  onAdminReturn,
  onTechnicalReview,
}) {
  const [finding, setFinding] = useState("");
  const [measurementForm, setMeasurementForm] = useState({});
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
    if (!reading) return;
    setFinding(reading.finding ?? "");
    setMeasurementForm(measurementFormValuesFromReading(reading));
    setSaveError(null);
    setSubmitError(null);
    setReturnReason("");
    setReturnError(null);
    setJcComment("");
    setJcRecommendation("");
    setJcError(null);
  }, [reading?.id]);

  if (!reading) {
    return (
      <EmptyState
        title="No Condition Monitoring reading selected"
        description="Select a reading from the list to view its details."
      />
    );
  }

  const leakDetected = reading.leakDe || reading.leakNde;
  const editable = Boolean(canWrite) && EDITABLE_STATUSES.has(reading.workflowStatus);
  const reviewable = reading.workflowStatus === "SUBMITTED";

  function setMeasurementField(key, value) {
    setMeasurementForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSaveDraft() {
    setSaving(true);
    setSaveError(null);
    try {
      await onSaveDraft?.(reading.id, {
        readingDate: reading.readingDate,
        measurements: buildManagedMeasurementsPayload(measurementForm),
        finding: finding || null,
      });
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    if (!window.confirm(`Submit Condition Monitoring reading ${reading.id} for review?`)) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onSubmit?.(reading.id);
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
    if (!window.confirm(`Return reading ${reading.id} for correction?`)) return;
    setReturning(true);
    setReturnError(null);
    try {
      await onAdminReturn?.(reading.id, returnReason.trim());
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
      RETURN: `Return reading ${reading.id} for correction?`,
      ACKNOWLEDGE: `Acknowledge reading ${reading.id}? This finalizes the record.`,
      APPROVE: `Technically approve reading ${reading.id}? This finalizes the record.`,
    }[action];
    if (!window.confirm(confirmMessage)) return;

    setJcActionPending(action);
    setJcError(null);
    try {
      await onTechnicalReview?.(reading.id, {
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
      <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>{reading.id}</h2>
        <WorkflowStatusBadge status={reading.workflowStatus} />
        <TechnicalOutcomeBadge outcome={reading.technicalOutcome} />
      </div>

      {reading.workflowStatus === "RETURNED_FOR_CORRECTION" && (
        <Card title="Returned for Correction">
          <p style={{ color: colors.danger, margin: 0 }}>
            Reason: {reading.returnReason || reading.technicalComment || "No reason recorded."}
          </p>
        </Card>
      )}

      <Card title="Reading Summary">
        <Field
          label="Equipment"
          value={reading.area ? `${reading.equipmentTag} — ${reading.area}` : reading.equipmentTag}
        />
        <Field label="Reading Date" value={reading.readingDate ?? "—"} />

        {editable ? (
          <div style={{ marginBottom: spacing.sm }}>
            <div style={{ color: colors.textMuted, fontSize: 12 }}>Pump Operating State</div>
            <select
              aria-label="Pump Operating State"
              style={fieldStyle}
              value={measurementForm.pumpOperatingState ?? ""}
              onChange={(event) => setMeasurementField("pumpOperatingState", event.target.value)}
            >
              <option value="">Not Recorded</option>
              {OPERATING_STATE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <Field label="Pump Operating State" value={reading.pumpOperatingState ?? "Not recorded"} />
        )}

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Seal Leak</div>
          <Badge variant={leakDetected ? "danger" : "success"}>
            {leakDetected ? "Leak detected" : "No leak"}
          </Badge>
        </div>
      </Card>

      <Card title="Mechanical Seal Leak Status (DE / NDE)">
        {/* Tri-state, explicit -- never inferred from a blank field. */}
        {editable ? (
          <div style={{ display: "flex", gap: spacing.sm }}>
            <div style={{ flex: 1 }}>
              <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>DE</div>
              <select
                aria-label="Leak Status DE"
                style={fieldStyle}
                value={measurementForm[LEAK_FIELD.deKey] ?? ""}
                onChange={(event) => setMeasurementField(LEAK_FIELD.deKey, event.target.value)}
              >
                {LEAK_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>NDE</div>
              <select
                aria-label="Leak Status NDE"
                style={fieldStyle}
                value={measurementForm[LEAK_FIELD.ndeKey] ?? ""}
                onChange={(event) => setMeasurementField(LEAK_FIELD.ndeKey, event.target.value)}
              >
                {LEAK_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : (
          <Field label="DE / NDE" value={`${leakLabel(reading.leakDe)} / ${leakLabel(reading.leakNde)}`} />
        )}
      </Card>

      <Card title="Temperatures (DE / NDE)">
        {/* MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 /
            MWO-LTSA-PM-CMON-FOUNDATION-CLEANUP-001 -- every canonical
            golden-evidence-backed temperature pair (migration-014's
            Mechseal/Bearing/Seal Gland/Stuffing Box, plus the legacy
            WO-CMON-001 Flushing/Quench/Flushing In/Flushing Out/Cooling
            Water In/Cooling Water Out/Water Jacket, ADR-CONDITION-
            MONITORING-001) is enterable from the one shared field list,
            rendered as inputs when editable. */}
        {MEASUREMENT_PAIR_FIELDS.filter((field) =>
          [
            "mechsealTempDe", "flushingTempDe", "quenchTempDe", "flushingInTempDe", "flushingOutTempDe",
            "coolingWaterInTempDe", "coolingWaterOutTempDe", "waterJacketTempDe",
            "stuffingBoxTempDe", "sealGlandTempDe", "bearingTempDe",
          ].includes(field.deKey)
        ).map((field) => (
          <MeasurementPairRow
            key={field.group}
            field={field}
            editable={editable}
            values={editable ? measurementForm : reading}
            onChange={setMeasurementField}
            formatValue={tempValue}
          />
        ))}
        {MEASUREMENT_SINGLE_FIELDS.filter((field) => field.unit === "°C").map((field) => (
          <MeasurementSingleRow
            key={field.key}
            field={field}
            editable={editable}
            values={editable ? measurementForm : reading}
            onChange={setMeasurementField}
            formatValue={tempValue}
          />
        ))}
      </Card>

      <Card title="Pressure / Vibration / Motor (DE / NDE)">
        {MEASUREMENT_SINGLE_FIELDS.filter((field) => field.unit === "bar" || field.unit === "A").map((field) => (
          <MeasurementSingleRow
            key={field.key}
            field={field}
            editable={editable}
            values={editable ? measurementForm : reading}
            onChange={setMeasurementField}
            formatValue={field.unit === "A" ? (value) => (value != null ? `${value} A` : "—") : pressureValue}
          />
        ))}
        {MEASUREMENT_PAIR_FIELDS.filter((field) =>
          ["quenchPressureDe", "verticalVibrationDe", "horizontalVibrationDe", "axialVibrationDe"].includes(field.deKey)
        ).map((field) => (
          <MeasurementPairRow
            key={field.group}
            field={field}
            editable={editable}
            values={editable ? measurementForm : reading}
            onChange={setMeasurementField}
            formatValue={field.unit === "bar" ? pressureValue : vibrationValue}
          />
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
          <p style={{ color: colors.text, margin: 0 }}>{reading.finding || "No finding recorded."}</p>
        )}
      </Card>

      {/* Phase 11 -- condition_monitoring_reading has no separate
          preliminary_recommendation column (migration 014's own schema);
          only pm_occurrence does. technical_recommendation still renders
          as its own card, honest about JC-only authority, never merged
          with Finding above. Read-only always: JC provenance, TAP can
          never edit this even while the record is otherwise editable. */}
      <Card title="Technical Recommendation — John Crane Engineer">
        <p style={{ color: colors.text, margin: 0 }}>
          {reading.technicalRecommendation || "No technical recommendation yet."}
        </p>
        {reading.technicalComment && (
          <p style={{ color: colors.textMuted, fontSize: 12, marginTop: spacing.xs }}>
            Comment: {reading.technicalComment}
          </p>
        )}
      </Card>

      {/* MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- source-document
          provenance, same convention as PMOccurrenceDetailPanel.jsx's own
          Source card -- N/A, never fabricated, for a live-entered record. */}
      <Card title="Source">
        <Field label="Source Workbook" value={reading.sourceWorkbookName ?? "N/A"} />
        <Field label="Source Sheet" value={reading.sourceSheetName ?? "N/A"} />
        <Field label="Source Row" value={reading.sourceRowNumber ?? "N/A"} />
      </Card>

      <Card title="Evidence">
        <EvidenceAttachments
          recordType={EVIDENCE_RECORD_TYPES.CONDITION_MONITORING_READING}
          recordCode={reading.id}
          canUpload={editable}
        />
      </Card>

      <Card title="Attribution">
        <Field label="Created" value={formatActor(reading.createdBy, reading.createdAt)} />
        <Field label="Updated" value={formatActor(reading.updatedBy, reading.updatedAt)} />
        <Field label="Submitted" value={formatActor(reading.submittedBy, reading.submittedAt)} />
        <Field label="Admin Review" value={formatActor(reading.reviewedBy, reading.reviewedAt)} />
        <Field
          label="Technical Review"
          value={formatActor(reading.technicalReviewedBy, reading.technicalReviewedAt)}
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

      <Card title="Related Schedule">
        {reading.scheduleCode ? (
          <Button onClick={() => onViewSchedule?.(reading.scheduleCode)}>{reading.scheduleCode}</Button>
        ) : (
          <div style={{ color: colors.textMuted }}>No owning schedule recorded.</div>
        )}
      </Card>

      <Card title="Quick Actions">
        <Button onClick={() => onViewAsset360?.(reading.equipmentTag)}>View Asset 360</Button>
      </Card>
    </div>
  );
}
