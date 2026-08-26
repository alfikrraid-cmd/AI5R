import { useState } from "react";
import { Badge, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { EmptySection } from "./KnowledgeCard";
import PMOccurrenceDetailPanel from "./PMOccurrenceDetailPanel";
import { isUnscheduledPlaceholder } from "../utils/pmMapping";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section E, "PREVENTIVE
// MAINTENANCE HISTORY". A pm_schedule_code that starts with "UNSCHEDULED::"
// is a historical-import placeholder (ltsa_hoc_pm_cm_upsert.py's own
// build_unscheduled_reference()), never a real schedule -- shown as its own
// visibly-labeled badge, never presented as if a real PM Schedule exists.
// This section never derives a schedule/frequency from these occurrences
// (Hard Rule: "Historical performed activity != PM plan"). MWO-LTSA-PM-
// CMON-SCHEDULE-LIFECYCLE-016 -- isUnscheduled is now the shared
// isUnscheduledPlaceholder (pmMapping.js), reused by
// PMOccurrenceDetailPanel.jsx's own identical guard, not redefined here.
const isUnscheduled = isUnscheduledPlaceholder;

function sortNewestFirst(occurrences) {
  return [...(occurrences ?? [])].sort((a, b) =>
    String(b.occurrenceDate ?? "").localeCompare(String(a.occurrenceDate ?? ""))
  );
}

export default function KnowledgePmHistorySection({ pmOccurrences, onOpenPump }) {
  const [expandedId, setExpandedId] = useState(null);
  const [visibleCount, setVisibleCount] = useState(5);

  const sorted = sortNewestFirst(pmOccurrences);

  if (sorted.length === 0) {
    return <EmptySection title="No PM History" description="No PM occurrences recorded for this pump yet." />;
  }

  return (
    <div>
      {sorted.slice(0, visibleCount).map((occurrence) => (
        <div key={occurrence.id} style={{ borderBottom: `1px solid ${colors.border}`, padding: `${spacing.xs}px 0` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: spacing.xs }}>
            <div>
              <strong>{occurrence.occurrenceDate ?? "N/A"}</strong>{" "}
              <Badge variant="info">{occurrence.workflowStatus ?? occurrence.status ?? "N/A"}</Badge>{" "}
              {isUnscheduled(occurrence.pmScheduleCode) ? (
                <Badge variant="warning">Historical / Unscheduled</Badge>
              ) : occurrence.pmScheduleCode ? (
                <Badge variant="success">Schedule: {occurrence.pmScheduleCode}</Badge>
              ) : null}
            </div>
            <Button onClick={() => setExpandedId((current) => (current === occurrence.id ? null : occurrence.id))}>
              {expandedId === occurrence.id ? "Hide" : "View Details"}
            </Button>
          </div>
          <p style={{ color: colors.textMuted, margin: `${spacing.xs}px 0 0` }}>
            {(occurrence.activities ?? []).filter((a) => a?.done).map((a) => a.description).join(", ") || "No activities recorded."}
          </p>
          {expandedId === occurrence.id && (
            <div style={{ marginTop: spacing.sm }}>
              <PMOccurrenceDetailPanel occurrence={occurrence} onOpenPump={onOpenPump} />
            </div>
          )}
        </div>
      ))}
      {visibleCount < sorted.length && (
        <div style={{ marginTop: spacing.sm }}>
          <Button onClick={() => setVisibleCount((count) => count + 5)}>
            Show more ({sorted.length - visibleCount} remaining)
          </Button>
        </div>
      )}
    </div>
  );
}
