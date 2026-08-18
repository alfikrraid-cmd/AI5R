import { useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import EvidenceAttachments, { EVIDENCE_RECORD_TYPES } from "./EvidenceAttachments";
import { TechnicalOutcomeBadge, WorkflowStatusBadge } from "./WorkflowStatusBadge";

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

// condition_monitoring_reading_repository.py's update_draft SETs every
// one of these columns from the `measurements` object it is given --
// there is no partial-column PATCH. To edit only `finding` without
// silently nulling out every temperature/pressure/vibration reading
// already on the record, this panel must always resend the record's own
// current values for every column not being edited here. Matches
// _MEASUREMENT_COLUMNS in that repository exactly (this session's own
// re-read of that file).
function buildMeasurementsPayload(reading) {
  return {
    flushing_temp_de: reading.flushingTempDe,
    flushing_temp_nde: reading.flushingTempNde,
    quench_temp_de: reading.quenchTempDe,
    quench_temp_nde: reading.quenchTempNde,
    flushing_in_temp_de: reading.flushingInTempDe,
    flushing_in_temp_nde: reading.flushingInTempNde,
    flushing_out_temp_de: reading.flushingOutTempDe,
    flushing_out_temp_nde: reading.flushingOutTempNde,
    cooling_water_in_temp_de: reading.coolingWaterInTempDe,
    cooling_water_in_temp_nde: reading.coolingWaterInTempNde,
    cooling_water_out_temp_de: reading.coolingWaterOutTempDe,
    cooling_water_out_temp_nde: reading.coolingWaterOutTempNde,
    mechseal_temp_de: reading.mechsealTempDe,
    mechseal_temp_nde: reading.mechsealTempNde,
    mechanical_seal_leak_de: reading.leakDe,
    mechanical_seal_leak_nde: reading.leakNde,
    water_jacket_temp_de: reading.waterJacketTempDe,
    water_jacket_temp_nde: reading.waterJacketTempNde,
    suction_temp: reading.suctionTemp,
    discharge_temp: reading.dischargeTemp,
    pump_operating_state: reading.pumpOperatingState,
    suction_pressure: reading.suctionPressure,
    discharge_pressure: reading.dischargePressure,
    quench_pressure_de: reading.quenchPressureDe,
    quench_pressure_nde: reading.quenchPressureNde,
    stuffing_box_temp_de: reading.stuffingBoxTempDe,
    stuffing_box_temp_nde: reading.stuffingBoxTempNde,
    seal_gland_temp_de: reading.sealGlandTempDe,
    seal_gland_temp_nde: reading.sealGlandTempNde,
    vertical_vibration_de: reading.verticalVibrationDe,
    vertical_vibration_nde: reading.verticalVibrationNde,
    horizontal_vibration_de: reading.horizontalVibrationDe,
    horizontal_vibration_nde: reading.horizontalVibrationNde,
    axial_vibration_de: reading.axialVibrationDe,
    axial_vibration_nde: reading.axialVibrationNde,
    bearing_temp_de: reading.bearingTempDe,
    bearing_temp_nde: reading.bearingTempNde,
    motor_current: reading.motorCurrent,
  };
}

const EDITABLE_STATUSES = new Set(["DRAFT", "RETURNED_FOR_CORRECTION"]);

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

  async function handleSaveDraft() {
    setSaving(true);
    setSaveError(null);
    try {
      await onSaveDraft?.(reading.id, {
        readingDate: reading.readingDate,
        measurements: buildMeasurementsPayload(reading),
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
        <Field label="Pump Operating State" value={reading.pumpOperatingState ?? "Not recorded"} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Seal Leak</div>
          <Badge variant={leakDetected ? "danger" : "success"}>
            {leakDetected ? "Leak detected" : "No leak"}
          </Badge>
        </div>
      </Card>

      <Card title="Temperatures (DE / NDE)">
        <Field
          label="Flushing"
          value={`${tempValue(reading.flushingTempDe)} / ${tempValue(reading.flushingTempNde)}`}
        />
        <Field
          label="Quench"
          value={`${tempValue(reading.quenchTempDe)} / ${tempValue(reading.quenchTempNde)}`}
        />
        <Field
          label="Flushing In (LBI)"
          value={`${tempValue(reading.flushingInTempDe)} / ${tempValue(reading.flushingInTempNde)}`}
        />
        <Field
          label="Flushing Out (LBO)"
          value={`${tempValue(reading.flushingOutTempDe)} / ${tempValue(reading.flushingOutTempNde)}`}
        />
        <Field
          label="Cooling Water In"
          value={`${tempValue(reading.coolingWaterInTempDe)} / ${tempValue(reading.coolingWaterInTempNde)}`}
        />
        <Field
          label="Cooling Water Out"
          value={`${tempValue(reading.coolingWaterOutTempDe)} / ${tempValue(reading.coolingWaterOutTempNde)}`}
        />
        <Field
          label="Mechseal"
          value={`${tempValue(reading.mechsealTempDe)} / ${tempValue(reading.mechsealTempNde)}`}
        />
        <Field
          label="Water Jacket"
          value={`${tempValue(reading.waterJacketTempDe)} / ${tempValue(reading.waterJacketTempNde)}`}
        />
        <Field
          label="Stuffing Box"
          value={`${tempValue(reading.stuffingBoxTempDe)} / ${tempValue(reading.stuffingBoxTempNde)}`}
        />
        <Field
          label="Seal Gland"
          value={`${tempValue(reading.sealGlandTempDe)} / ${tempValue(reading.sealGlandTempNde)}`}
        />
        <Field
          label="Bearing"
          value={`${tempValue(reading.bearingTempDe)} / ${tempValue(reading.bearingTempNde)}`}
        />
        <Field label="Suction" value={tempValue(reading.suctionTemp)} />
        <Field label="Discharge" value={tempValue(reading.dischargeTemp)} />
      </Card>

      <Card title="Pressure / Vibration / Motor (DE / NDE)">
        <Field label="Suction Pressure" value={pressureValue(reading.suctionPressure)} />
        <Field label="Discharge Pressure" value={pressureValue(reading.dischargePressure)} />
        <Field
          label="Quench Pressure"
          value={`${pressureValue(reading.quenchPressureDe)} / ${pressureValue(reading.quenchPressureNde)}`}
        />
        <Field
          label="Vertical Vibration"
          value={`${vibrationValue(reading.verticalVibrationDe)} / ${vibrationValue(reading.verticalVibrationNde)}`}
        />
        <Field
          label="Horizontal Vibration"
          value={`${vibrationValue(reading.horizontalVibrationDe)} / ${vibrationValue(reading.horizontalVibrationNde)}`}
        />
        <Field
          label="Axial Vibration"
          value={`${vibrationValue(reading.axialVibrationDe)} / ${vibrationValue(reading.axialVibrationNde)}`}
        />
        <Field label="Motor Current" value={reading.motorCurrent != null ? `${reading.motorCurrent} A` : "—"} />
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
          with Finding above. */}
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
