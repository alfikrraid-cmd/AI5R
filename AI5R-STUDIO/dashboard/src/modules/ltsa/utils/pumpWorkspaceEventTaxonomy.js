/**
 * Maps the real, already-fetched Asset 360 event stream (5 real sources:
 * WO, MH, CM, PM, CMON -- see maintenanceHistory.js's
 * buildAssetEventStream) onto the approved Pump Workspace design's own
 * 4-chip Timeline taxonomy (Semua/PM/CM/Breakdown --
 * DESIGN/LTSA/PUMP_WORKSPACE/pump-workspace.html).
 *
 * Interpretation decisions (disclosed, not silent -- no field is
 * fabricated, every value read below is already real):
 *
 * - PM (PM Occurrence) -> design tier "pm".
 * - CM (CM Report) is split using its own already-real `downtimeHours`
 *   field (present on every mapped CM event's `raw` payload, per
 *   mapCMReportToEvent): downtimeHours > 0 (unplanned downtime actually
 *   occurred) -> design tier "breakdown"; otherwise -> design tier "cm".
 *   This is how the design's own example data already distinguishes the
 *   two ("Corrective Maintenance" vs "Breakdown -- Kegagalan Bearing DE,
 *   Unplanned downtime 6.5 jam"), applied to real data instead of invented.
 * - WO, MH, CMON have no corresponding chip in the approved design (only
 *   Semua/PM/CM/Breakdown exist -- adding a chip would be a redesign).
 *   They fall back to the design's own "alert" tier, the one bucket the
 *   design itself uses for events outside its three named chips (see
 *   TIMELINE[0], type "alert", not matched by any chip filter).
 */

const CHIP_ORDER = ["all", "pm", "cm", "breakdown"];

export const TIMELINE_FILTER_CHIPS = [
  { id: "all", label: "Semua" },
  { id: "pm", label: "PM" },
  { id: "cm", label: "CM" },
  { id: "breakdown", label: "Breakdown" },
];

export function designTierForEvent(event) {
  if (event.type === "PM") {
    return "pm";
  }

  if (event.type === "CM") {
    const downtimeHours = event.raw?.downtimeHours;
    return typeof downtimeHours === "number" && downtimeHours > 0 ? "breakdown" : "cm";
  }

  return "alert";
}

const TAG_LABEL = {
  pm: "PM",
  cm: "CM",
  breakdown: "BREAKDOWN",
  alert: "ALERT",
};

export function designTagLabel(tier) {
  return TAG_LABEL[tier] ?? tier.toUpperCase();
}

/** Real event -> the shape PumpWorkspaceTimeline renders. No field is invented. */
export function toWorkspaceTimelineItem(event) {
  const tier = designTierForEvent(event);

  return {
    id: event.id,
    tier,
    tag: designTagLabel(tier),
    title: event.title,
    date: event.date,
    assignedTechnician: event.assignedTechnician,
  };
}

export function isChipId(id) {
  return CHIP_ORDER.includes(id);
}
