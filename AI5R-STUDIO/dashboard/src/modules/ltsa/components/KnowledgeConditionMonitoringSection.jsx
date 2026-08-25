import { useState } from "react";
import { Badge, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { EmptySection } from "./KnowledgeCard";
import TemperatureTrendChart from "./TemperatureTrendChart";
import ConditionMonitoringReadingDetailPanel from "./ConditionMonitoringReadingDetailPanel";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section C, "CONDITION MONITORING".
// All temperature points mapConditionMonitoringReadingRecord already
// carries (ADR-CONDITION-MONITORING-001's full field set) -- NULL is
// rendered as N/A, never substituted with 0.
const TEMP_PAIRS = [
  { label: "Flushing", deKey: "flushingTempDe", ndeKey: "flushingTempNde" },
  { label: "Quench", deKey: "quenchTempDe", ndeKey: "quenchTempNde" },
  { label: "Flushing In", deKey: "flushingInTempDe", ndeKey: "flushingInTempNde" },
  { label: "Flushing Out", deKey: "flushingOutTempDe", ndeKey: "flushingOutTempNde" },
  { label: "Cooling Water In", deKey: "coolingWaterInTempDe", ndeKey: "coolingWaterInTempNde" },
  { label: "Cooling Water Out", deKey: "coolingWaterOutTempDe", ndeKey: "coolingWaterOutTempNde" },
  { label: "Mechanical Seal", deKey: "mechsealTempDe", ndeKey: "mechsealTempNde" },
  { label: "Water Jacket", deKey: "waterJacketTempDe", ndeKey: "waterJacketTempNde" },
];

function tempValue(value) {
  return value !== null && value !== undefined ? `${value}°C` : "N/A";
}

function leakLabel(value) {
  if (value === true) return "Detected";
  if (value === false) return "No Leak";
  return "Not Recorded";
}

function sortNewestFirst(readings) {
  return [...(readings ?? [])].sort((a, b) => String(b.readingDate ?? "").localeCompare(String(a.readingDate ?? "")));
}

export default function KnowledgeConditionMonitoringSection({ readings, onOpenPump }) {
  const [expandedId, setExpandedId] = useState(null);
  const [historyVisibleCount, setHistoryVisibleCount] = useState(5);

  const sorted = sortNewestFirst(readings);
  const latest = sorted[0] ?? null;

  if (!latest) {
    return <EmptySection title="No Condition Monitoring readings" description="No readings recorded for this pump yet." />;
  }

  return (
    <div>
      <div style={{ marginBottom: spacing.md }}>
        <div style={{ display: "flex", gap: spacing.sm, alignItems: "center", flexWrap: "wrap", marginBottom: spacing.xs }}>
          <strong>Latest: {latest.readingDate ?? "N/A"}</strong>
          <Badge variant="info">{latest.pumpOperatingState ?? "N/A"}</Badge>
          <Badge variant={latest.leakDe || latest.leakNde ? "danger" : "success"}>
            Leak DE: {leakLabel(latest.leakDe)} · NDE: {leakLabel(latest.leakNde)}
          </Badge>
        </div>
        <p style={{ color: colors.text, margin: 0 }}>{latest.finding || "No finding recorded."}</p>
      </div>

      <div style={{ marginBottom: spacing.md }}>
        <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>Temperatures (DE / NDE)</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: spacing.xs }}>
          {TEMP_PAIRS.map((pair) => (
            <div key={pair.label} style={{ background: colors.panel, border: `1px solid ${colors.border}`, borderRadius: spacing.xs, padding: spacing.xs }}>
              <div style={{ color: colors.textMuted, fontSize: 11 }}>{pair.label}</div>
              <div style={{ color: colors.text }}>
                {tempValue(latest[pair.deKey])} / {tempValue(latest[pair.ndeKey])}
              </div>
            </div>
          ))}
          <div style={{ background: colors.panel, border: `1px solid ${colors.border}`, borderRadius: spacing.xs, padding: spacing.xs }}>
            <div style={{ color: colors.textMuted, fontSize: 11 }}>Suction / Discharge</div>
            <div style={{ color: colors.text }}>
              {tempValue(latest.suctionTemp)} / {tempValue(latest.dischargeTemp)}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: spacing.md }}>
        <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>Temperature Trend</div>
        <TemperatureTrendChart readings={sorted} />
      </div>

      <div>
        <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
          Reading History ({sorted.length})
        </div>
        {sorted.slice(0, historyVisibleCount).map((reading) => (
          <div key={reading.id} style={{ borderBottom: `1px solid ${colors.border}`, padding: `${spacing.xs}px 0` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>
                {reading.readingDate ?? "N/A"} · {reading.pumpOperatingState ?? "N/A"} ·{" "}
                {reading.leakDe || reading.leakNde ? "Leak detected" : "No leak"}
              </span>
              <Button onClick={() => setExpandedId((current) => (current === reading.id ? null : reading.id))}>
                {expandedId === reading.id ? "Hide" : "View Details"}
              </Button>
            </div>
            {expandedId === reading.id && (
              <div style={{ marginTop: spacing.sm }}>
                <ConditionMonitoringReadingDetailPanel reading={reading} onViewAsset360={onOpenPump} />
              </div>
            )}
          </div>
        ))}
        {historyVisibleCount < sorted.length && (
          <div style={{ marginTop: spacing.sm }}>
            <Button onClick={() => setHistoryVisibleCount((count) => count + 5)}>
              Show more ({sorted.length - historyVisibleCount} remaining)
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
