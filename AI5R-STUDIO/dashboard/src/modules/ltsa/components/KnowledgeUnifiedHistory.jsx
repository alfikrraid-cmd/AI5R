import { useMemo, useState } from "react";
import { Badge, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import PMOccurrenceDetailPanel from "./PMOccurrenceDetailPanel";
import ConditionMonitoringReadingDetailPanel from "./ConditionMonitoringReadingDetailPanel";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section D, "Unified Maintenance
// History". This is DISPLAY-ONLY merging: each row still points at its own
// real, separate underlying record (pm_occurrence / condition_monitoring_
// reading / cm_report / work_order); nothing is merged in the database or
// even in a shared in-memory shape beyond {date, type, record} for sorting
// and same-day grouping. "Same Visit" is presentation logic only, applied
// when a real PM record and a real CMON record share both pump (the whole
// page is already scoped to one) and calendar date -- same rule this
// session's own PumpOpenDesignView.jsx already proved out and shipped to
// production (sharedPmCmonDates), re-expressed here against this page's
// own camelCase mapped shapes (occurrenceDate/readingDate) rather than
// PumpLifecycle's differently-shaped timeline events.

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "PM", label: "PM" },
  { key: "CMON", label: "CMON" },
  { key: "CM", label: "CM" },
  { key: "WO", label: "WO" },
  { key: "SEAL", label: "Seal" },
  { key: "BREAKDOWN", label: "Breakdown" },
];

const PAGE_SIZE = 10;

function dayOf(value) {
  return value ? String(value).slice(0, 10) : null;
}

function buildRows({ pmOccurrences, conditionMonitoringReadings, workOrders, cmHistory, breakdownHistory }) {
  const rows = [];

  for (const occurrence of pmOccurrences ?? []) {
    rows.push({
      key: `PM:${occurrence.id}`,
      type: "PM",
      date: dayOf(occurrence.occurrenceDate),
      record: occurrence,
    });
  }
  for (const reading of conditionMonitoringReadings ?? []) {
    rows.push({
      key: `CMON:${reading.id}`,
      type: "CMON",
      date: dayOf(reading.readingDate),
      record: reading,
    });
  }
  for (const workOrder of workOrders ?? []) {
    rows.push({
      key: `WO:${workOrder.id}`,
      type: "WO",
      date: dayOf(workOrder.dueDate ?? workOrder.createdDate),
      record: workOrder,
    });
  }
  // cmHistory/breakdownHistory arrive as the existing lossy {id,name,meta}
  // shape (mapRefItem) -- cm_report has 0 rows in production today (this
  // session's own verified DB count), so this category is real, honest,
  // and currently-empty, not a placeholder.
  for (const record of cmHistory ?? []) {
    rows.push({ key: `CM:${record.id}`, type: "CM", date: dayOf(record.meta), record });
  }
  for (const record of breakdownHistory ?? []) {
    rows.push({ key: `BREAKDOWN:${record.id}`, type: "BREAKDOWN", date: dayOf(record.meta), record });
  }

  return rows.sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")));
}

function sameVisitDates(rows) {
  const pmDates = new Set(rows.filter((row) => row.type === "PM" && row.date).map((row) => row.date));
  const cmonDates = new Set(rows.filter((row) => row.type === "CMON" && row.date).map((row) => row.date));
  const shared = new Set();
  for (const date of pmDates) {
    if (cmonDates.has(date)) shared.add(date);
  }
  return shared;
}

function pmSummary(occurrence) {
  const checklist = occurrence.activities ?? [];
  const done = checklist.filter((entry) => entry?.done).map((entry) => entry.description);
  const status = occurrence.workflowStatus ?? occurrence.status ?? "N/A";
  return done.length > 0 ? `${status} — ${done.join(", ")}` : status;
}

function cmonSummary(reading) {
  const state = reading.pumpOperatingState ?? "N/A";
  if (reading.finding) return `${state} — ${reading.finding}`;
  if (reading.leakDe || reading.leakNde) return `${state} — Leak detected`;
  return `${state} — No leak recorded`;
}

const TYPE_LABEL = {
  PM: "PM",
  CMON: "CONDITION MONITORING",
  CM: "CORRECTIVE MAINTENANCE",
  WO: "WORK ORDER",
  BREAKDOWN: "BREAKDOWN",
};

function Row({ row, isSameVisit, expanded, onToggle, onOpenPump }) {
  const label = TYPE_LABEL[row.type] ?? row.type;
  let summary = "N/A";
  if (row.type === "PM") summary = pmSummary(row.record);
  else if (row.type === "CMON") summary = cmonSummary(row.record);
  else if (row.record?.name) summary = row.record.name;

  return (
    <div style={{ borderBottom: `1px solid ${colors.border}`, padding: `${spacing.sm}px 0` }} data-testid={`history-row-${row.key}`}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: spacing.xs }}>
        <div>
          <strong>{row.date ?? "N/A"}</strong>{" "}
          <Badge variant="info">{label}</Badge>
          {isSameVisit ? <Badge variant="success"> Same Visit • PM + Condition Monitoring</Badge> : null}
        </div>
        {(row.type === "PM" || row.type === "CMON") && (
          <Button onClick={onToggle}>{expanded ? "Hide Details" : "View Details"}</Button>
        )}
      </div>
      <p style={{ color: colors.textMuted, margin: `${spacing.xs}px 0 0` }}>{summary}</p>

      {expanded && row.type === "PM" && (
        <div style={{ marginTop: spacing.sm }}>
          <PMOccurrenceDetailPanel occurrence={row.record} onOpenPump={onOpenPump} />
        </div>
      )}
      {expanded && row.type === "CMON" && (
        <div style={{ marginTop: spacing.sm }}>
          <ConditionMonitoringReadingDetailPanel reading={row.record} onViewAsset360={onOpenPump} />
        </div>
      )}
    </div>
  );
}

export default function KnowledgeUnifiedHistory({
  pmOccurrences,
  conditionMonitoringReadings,
  workOrders,
  cmHistory,
  breakdownHistory,
  onOpenPump,
}) {
  const [filter, setFilter] = useState("ALL");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [expandedKey, setExpandedKey] = useState(null);

  const allRows = useMemo(
    () => buildRows({ pmOccurrences, conditionMonitoringReadings, workOrders, cmHistory, breakdownHistory }),
    [pmOccurrences, conditionMonitoringReadings, workOrders, cmHistory, breakdownHistory]
  );
  const sameVisit = useMemo(() => sameVisitDates(allRows), [allRows]);

  const filteredRows = filter === "ALL" ? allRows : allRows.filter((row) => row.type === filter);
  const visibleRows = filteredRows.slice(0, visibleCount);

  if (allRows.length === 0) {
    return <p style={{ color: colors.textMuted }}>No maintenance history recorded for this pump yet.</p>;
  }

  return (
    <div data-testid="unified-history">
      <div role="group" aria-label="History filter" style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs, marginBottom: spacing.sm }}>
        {FILTERS.map((option) => (
          <button
            key={option.key}
            type="button"
            aria-pressed={option.key === filter}
            onClick={() => {
              setFilter(option.key);
              setVisibleCount(PAGE_SIZE);
            }}
            style={{
              padding: `2px ${spacing.sm}px`,
              borderRadius: spacing.xs,
              border: `1px solid ${colors.border}`,
              background: option.key === filter ? colors.accent : "transparent",
              color: option.key === filter ? colors.background : colors.text,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            {option.label}
          </button>
        ))}
      </div>

      {filteredRows.length === 0 ? (
        <p style={{ color: colors.textMuted }}>No {filter} events recorded for this pump.</p>
      ) : (
        <>
          {visibleRows.map((row) => (
            <Row
              key={row.key}
              row={row}
              isSameVisit={Boolean(row.date && sameVisit.has(row.date) && (row.type === "PM" || row.type === "CMON"))}
              expanded={expandedKey === row.key}
              onToggle={() => setExpandedKey((current) => (current === row.key ? null : row.key))}
              onOpenPump={onOpenPump}
            />
          ))}
          {visibleCount < filteredRows.length && (
            <div style={{ marginTop: spacing.sm }}>
              <Button onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}>
                Show more ({filteredRows.length - visibleCount} remaining)
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
