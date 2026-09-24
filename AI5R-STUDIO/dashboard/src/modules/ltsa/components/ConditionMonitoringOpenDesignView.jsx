import { useState } from "react";
import AssetIdentityHeader, { HealthCard } from "./AssetIdentityHeader";
import WorkspaceTabStrip from "./WorkspaceTabStrip";
import { IconClipboard } from "./PumpWorkspaceIcons";
import { InfoRow, RefGroup } from "./open-design";
import { WorkflowStatusBadge, TechnicalOutcomeBadge } from "./WorkflowStatusBadge";
import { isUnscheduledPlaceholder } from "../utils/conditionMonitoringMapping";
import TemperatureTrendChart from "./TemperatureTrendChart";
import { leakPresentationFor } from "../utils/leakSemantics";

/**
 * UI-D3.2 -- Condition Monitoring Open Design View (APP-CMON-001)
 *
 * Migrated to established AI5R Open Design reference:
 * - AssetIdentityHeader (Asset-centric: supports PUMP, LIQUID RING COMPRESSOR, UNCLASSIFIED, etc.)
 * - WorkspaceTabStrip with 4 canonical tabs:
 *     1. Overview
 *     2. Measurements (all 35 DE/NDE measurement fields preserved and grouped)
 *     3. Trends (TemperatureTrendChart preserved; vibration unavailable note, no fake chart)
 *     4. History (workflow attribution, source provenance, related readings)
 * - Zero fake business data (no fabricated health/severity/condition scores).
 * - Honest tri-state leak state (Detected / Not Detected / N/A).
 */

const dataEmptyReason = "No engineering data";

function tempValue(value) {
  return value != null ? `${value} °C` : "—";
}

function pressureValue(value) {
  return value != null ? `${value} bar` : "—";
}

function vibrationValue(value) {
  return value != null ? `${value} mm/s` : "—";
}

function currentAmpValue(value) {
  return value != null ? `${value} A` : "—";
}

function leakFieldLabel(value) {
  if (value === true) return "Leak Detected";
  if (value === false) return "No Leak";
  return "Not Recorded";
}

function formatActor(actorId, timestamp) {
  if (!actorId && !timestamp) return "—";
  return timestamp ? `${actorId || "unknown"} · ${timestamp}` : actorId || "unknown";
}

const CM_TABS = [
  { key: "overview", label: "Overview" },
  { key: "measurements", label: "Measurements" },
  { key: "trends", label: "Trends" },
  { key: "history", label: "History" },
];

export default function ConditionMonitoringOpenDesignView({
  reading,
  relatedReadings = [],
  assetReadings = [],
  onOpenAsset360,
  onViewSchedule,
  onBack,
  onReportMeasuring,
}) {
  const [activeTab, setActiveTab] = useState("overview");

  // LTSA_CM_UI_REMEDIATION_R1C -- canonical tri-state (a one-sided record is partial, not "Not Detected").
  const leakSummary = leakPresentationFor(reading.leakDe, reading.leakNde);
  const leakDisplay = leakSummary.label;
  const leakTone = leakSummary.tone;

  const hasSchedule = reading.scheduleCode && !isUnscheduledPlaceholder(reading.scheduleCode);
  const assetTypeLabel = reading.assetType ? reading.assetType : "Equipment";

  return (
    <div className="ltsa-open-design" data-testid="cmon-open-design">
      <AssetIdentityHeader
        icon={<IconClipboard />}
        tag={reading.id}
        name={reading.readingDate ? `Reading — ${reading.readingDate}` : "Reading — date unknown"}
        subtitle={
          reading.equipmentTag
            ? `${assetTypeLabel} ${reading.equipmentTag}${reading.area ? ` · ${reading.area}` : ""}`
            : "Equipment unknown"
        }
        onBack={onBack}
      >
        <HealthCard
          label="Workflow"
          value={reading.workflowStatus ? reading.workflowStatus.replace(/_/g, " ") : "N/A"}
          tone={reading.workflowStatus === "FINALIZED" ? "normal" : "neutral"}
        />
        <HealthCard label="Seal Leak" value={leakDisplay} tone={leakTone} />
      </AssetIdentityHeader>

      <WorkspaceTabStrip items={CM_TABS} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <div className="workspace-overview-grid">
          <div className="workspace-overview-card" data-od-id="identity-section">
            <div className="eyebrow">Reading Information</div>
            <InfoRow label="Reading ID" value={reading.id} valueClassName="mono" />
            <InfoRow label="Reading Date" value={reading.readingDate ?? "N/A"} />
            <InfoRow label="Schedule" value={hasSchedule ? reading.scheduleCode : "No linked schedule / historical import"} />
            <InfoRow label="Operating State" value={reading.pumpOperatingState ?? "Not recorded"} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Asset Information</div>
            <InfoRow label="Equipment / Asset" value={reading.equipmentTag ?? "N/A"} />
            <InfoRow label="Asset Type" value={assetTypeLabel} />
            <InfoRow label="Area" value={reading.area ?? "N/A"} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Quick Actions</div>
            <div className="workspace-quick-actions">
              {reading.equipmentTag && (
                <button
                  type="button"
                  className="workspace-quick-action-btn"
                  onClick={() => onOpenAsset360?.(reading.equipmentTag)}
                  data-od-id="action-bar-open-asset360"
                >
                  View Asset 360 →
                </button>
              )}
              {hasSchedule && (
                <button
                  type="button"
                  className="workspace-quick-action-btn"
                  onClick={() => onViewSchedule?.(reading.scheduleCode)}
                  data-od-id="action-bar-open-schedule"
                >
                  Buka Schedule →
                </button>
              )}
              <button
                type="button"
                className="workspace-quick-action-btn"
                onClick={() => setActiveTab("measurements")}
              >
                View Measurements →
              </button>
              <button
                type="button"
                className="workspace-quick-action-btn"
                onClick={() => setActiveTab("trends")}
              >
                View Trends →
              </button>
              <button
                type="button"
                className="workspace-quick-action-btn"
                onClick={onReportMeasuring}
                data-testid="open-report-measuring"
              >
                Report Measuring →
              </button>
              <button
                type="button"
                className="workspace-quick-action-btn"
                onClick={() => setActiveTab("history")}
              >
                View History →
              </button>
            </div>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Measurement Summary</div>
            <InfoRow
              label="Mechanical Seal Temp (DE / NDE)"
              value={`${tempValue(reading.mechsealTempDe)} / ${tempValue(reading.mechsealTempNde)}`}
            />
            <InfoRow
              label="Seal Leak (DE / NDE)"
              value={`${leakFieldLabel(reading.leakDe)} / ${leakFieldLabel(reading.leakNde)}`}
            />
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
              Full 35-field DE/NDE measurement set is available in the Measurements tab and in Reading Detail below.
            </p>
          </div>

          {reading.finding && (
            <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
              <div className="eyebrow">Finding</div>
              <h2 className="assessment-headline">{reading.finding}</h2>
            </div>
          )}

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Technical Recommendation — John Crane Engineer</div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
              <WorkflowStatusBadge status={reading.workflowStatus} />
              <TechnicalOutcomeBadge outcome={reading.technicalOutcome} />
            </div>
            {reading.technicalRecommendation ? (
              <h2 className="assessment-headline">{reading.technicalRecommendation}</h2>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No technical recommendation yet.</p>
            )}
            {reading.technicalComment && (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
                Comment: {reading.technicalComment}
              </p>
            )}
          </div>
        </div>
      )}

      {activeTab === "measurements" && (
        <div className="workspace-tab-body">
          <div className="workspace-overview-grid">
            {/* 1. Vibration */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Vibration (mm/s)</div>
              <InfoRow
                label="Vertical Vibration (DE / NDE)"
                value={`${vibrationValue(reading.verticalVibrationDe)} / ${vibrationValue(reading.verticalVibrationNde)}`}
              />
              <InfoRow
                label="Horizontal Vibration (DE / NDE)"
                value={`${vibrationValue(reading.horizontalVibrationDe)} / ${vibrationValue(reading.horizontalVibrationNde)}`}
              />
              <InfoRow
                label="Axial Vibration (DE / NDE)"
                value={`${vibrationValue(reading.axialVibrationDe)} / ${vibrationValue(reading.axialVibrationNde)}`}
              />
            </div>

            {/* 2. Bearing Temperature */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Bearing Temperature (°C)</div>
              <InfoRow
                label="Bearing Temp (DE / NDE)"
                value={`${tempValue(reading.bearingTempDe)} / ${tempValue(reading.bearingTempNde)}`}
              />
            </div>

            {/* 3. Mechanical Seal & Gland */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Mechanical Seal & Gland</div>
              <InfoRow
                label="Mechanical Seal Temp (DE / NDE)"
                value={`${tempValue(reading.mechsealTempDe)} / ${tempValue(reading.mechsealTempNde)}`}
              />
              <InfoRow
                label="Stuffing Box Temp (DE / NDE)"
                value={`${tempValue(reading.stuffingBoxTempDe)} / ${tempValue(reading.stuffingBoxTempNde)}`}
              />
              <InfoRow
                label="Seal Gland Temp (DE / NDE)"
                value={`${tempValue(reading.sealGlandTempDe)} / ${tempValue(reading.sealGlandTempNde)}`}
              />
              <InfoRow
                label="Mechanical Seal Leak (DE / NDE)"
                value={`${leakFieldLabel(reading.leakDe)} / ${leakFieldLabel(reading.leakNde)}`}
              />
            </div>

            {/* 4. Flushing & Quench */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Flushing & Quench</div>
              <InfoRow
                label="Flushing Temp (DE / NDE)"
                value={`${tempValue(reading.flushingTempDe)} / ${tempValue(reading.flushingTempNde)}`}
              />
              <InfoRow
                label="Quench Temp (DE / NDE)"
                value={`${tempValue(reading.quenchTempDe)} / ${tempValue(reading.quenchTempNde)}`}
              />
              <InfoRow
                label="Flushing In Temp — LBI (DE / NDE)"
                value={`${tempValue(reading.flushingInTempDe)} / ${tempValue(reading.flushingInTempNde)}`}
              />
              <InfoRow
                label="Flushing Out Temp — LBO (DE / NDE)"
                value={`${tempValue(reading.flushingOutTempDe)} / ${tempValue(reading.flushingOutTempNde)}`}
              />
              <InfoRow
                label="Quench Pressure (DE / NDE)"
                value={`${pressureValue(reading.quenchPressureDe)} / ${pressureValue(reading.quenchPressureNde)}`}
              />
            </div>

            {/* 5. Cooling */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Cooling System (°C)</div>
              <InfoRow
                label="Cooling Water In Temp (DE / NDE)"
                value={`${tempValue(reading.coolingWaterInTempDe)} / ${tempValue(reading.coolingWaterInTempNde)}`}
              />
              <InfoRow
                label="Cooling Water Out Temp (DE / NDE)"
                value={`${tempValue(reading.coolingWaterOutTempDe)} / ${tempValue(reading.coolingWaterOutTempNde)}`}
              />
              <InfoRow
                label="Water Jacket Temp (DE / NDE)"
                value={`${tempValue(reading.waterJacketTempDe)} / ${tempValue(reading.waterJacketTempNde)}`}
              />
            </div>

            {/* 6. Process Conditions & Operating State */}
            <div className="workspace-overview-card">
              <div className="eyebrow">Process Conditions</div>
              <InfoRow label="Suction Temp" value={tempValue(reading.suctionTemp)} />
              <InfoRow label="Discharge Temp" value={tempValue(reading.dischargeTemp)} />
              <InfoRow label="Suction Pressure" value={pressureValue(reading.suctionPressure)} />
              <InfoRow label="Discharge Pressure" value={pressureValue(reading.dischargePressure)} />
              <InfoRow label="Motor Current" value={currentAmpValue(reading.motorCurrent)} />
              <InfoRow label="Operating State" value={reading.pumpOperatingState ?? "Not recorded"} />
            </div>
          </div>
        </div>
      )}

      {activeTab === "trends" && (
        <div className="workspace-tab-body">
          <div className="workspace-overview-card">
            <div className="eyebrow">Temperature Trend — {reading.equipmentTag ?? "Unknown Asset"}</div>
            <div style={{ marginTop: "var(--space-3)" }}>
              <TemperatureTrendChart readings={assetReadings} />
            </div>
          </div>
          <div className="workspace-overview-card" style={{ marginTop: "var(--space-3)" }}>
            <div className="eyebrow">Vibration Trend</div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
              Vibration historical trend series is unavailable. Vibration readings are tracked per visit under the Measurements tab.
            </p>
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="workspace-tab-body">
          <div className="workspace-overview-grid">
            <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
              <RefGroup
                title="Reading History — Same Asset"
                items={relatedReadings.map((item) => ({
                  key: item.id,
                  name: item.id,
                  meta: item.readingDate ? `Reading ${item.readingDate}` : "Date unknown",
                  flagLabel: item.workflowStatus,
                }))}
                emptyReason={dataEmptyReason}
              />
            </div>

            <div className="workspace-overview-card">
              <div className="eyebrow">Workflow & Review Attribution</div>
              <InfoRow label="Created" value={formatActor(reading.createdBy, reading.createdAt)} />
              <InfoRow label="Updated" value={formatActor(reading.updatedBy, reading.updatedAt)} />
              <InfoRow label="Submitted" value={formatActor(reading.submittedBy, reading.submittedAt)} />
              <InfoRow label="Admin Review" value={formatActor(reading.reviewedBy, reading.reviewedAt)} />
              <InfoRow
                label="Technical Review"
                value={formatActor(reading.technicalReviewedBy, reading.technicalReviewedAt)}
              />
            </div>

            <div className="workspace-overview-card">
              <div className="eyebrow">Source Document Provenance</div>
              <InfoRow label="Source Workbook" value={reading.sourceWorkbookName ?? "N/A (Live entered)"} />
              <InfoRow label="Source Sheet" value={reading.sourceSheetName ?? "N/A"} />
              <InfoRow
                label="Source Row"
                value={reading.sourceRowNumber != null ? String(reading.sourceRowNumber) : "N/A"}
              />
              {reading.sourceReference && <InfoRow label="Source Reference" value={reading.sourceReference} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
