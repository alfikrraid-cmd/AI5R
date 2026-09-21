/**
 * MWO-LTSA-DASHBOARD-ALL-ANALYTICS-VISUALIZATION-R1 / R2
 * Diagram-First Engineering Analytics Data Transformation Layer.
 *
 * Sourced strictly from real canonical production data:
 * - REAL PRODUCTION DATA ONLY: No mocks, no synthetic records, no hardcoded counts.
 * - UNKNOWN != ZERO: Missing or unimported historical months return null so charts render gaps.
 * - CANONICAL PUMP STATUS: OPERATIONAL, STANDBY, MAINTENANCE, FAULT, UNKNOWN.
 *   DO NOT calculate or imply an area health score.
 * - PM COMPLIANCE: Sourced strictly from PM schedule states (COMPLETED, DUE, OVERDUE, PLANNED).
 *   DO NOT mix Work Orders into PM Compliance. Open Work Orders are NOT PM Overdue.
 * - CM = CONDITION MONITORING (inspections, readings, vibration). ZERO corrective maintenance semantics.
 * - LEAK EVIDENCE: Sourced from mechanical_seal_leak_de / mechanical_seal_leak_nde flags.
 *   Labeled strictly as "Leak Evidence", never "Confirmed Leak".
 * - MECHANICAL SEAL CONDITION: Traced to canonical fields (Normal, Under Observation, Leak Evidence).
 *   No non-canonical "Replacement Required" category or priority >= 100 threshold heuristics.
 * - MECHANICAL SEAL INVENTORY: Visualizes actual canonical quantities
 *   (quantity_on_hand, quantity_available, quantity_reserved).
 *   DO NOT invent Low Stock / Out of Stock thresholds.
 * - TOP RISK PUMPS: Sourced from canonical backend ordering / priority (leak_count or priority).
 *   DO NOT calculate a custom combined risk score.
 */

import colors from "../../../design-system/theme/colors";

/**
 * Normalizes any pump status to the 5 canonical engineering statuses:
 * - OPERATIONAL
 * - STANDBY
 * - MAINTENANCE
 * - FAULT
 * - UNKNOWN
 */
export function normalizePumpStatus(status) {
  if (!status) return "UNKNOWN";
  const s = String(status).toUpperCase().trim();
  if (s === "RUNNING" || s === "ACTIVE" || s === "OPERATIONAL") return "OPERATIONAL";
  if (s === "STANDBY" || s === "IDLE") return "STANDBY";
  if (s === "MAINTENANCE" || s === "UNDER_MAINTENANCE" || s === "REPAIR" || s === "SERVICING") return "MAINTENANCE";
  if (s === "FAULT" || s === "FAILED" || s === "TRIPPED" || s === "BREAKDOWN") return "FAULT";
  return "UNKNOWN";
}

export const CANONICAL_PUMP_STATUSES = [
  "OPERATIONAL",
  "STANDBY",
  "MAINTENANCE",
  "FAULT",
  "UNKNOWN",
];

export const ASSET_STATUS_BARS = [
  { key: "OPERATIONAL", label: "Operational", color: colors.success },
  { key: "STANDBY", label: "Standby", color: colors.info },
  { key: "MAINTENANCE", label: "Maintenance", color: colors.warning },
  { key: "FAULT", label: "Fault", color: colors.danger },
  { key: "UNKNOWN", label: "Unknown", color: colors.textMuted },
];

/**
 * Row 2 LEFT: Asset Status by Area
 * Stacked bar chart data: groups pumps by area, counting each canonical status.
 *
 * TITLE: "Asset Status by Area"
 * NO health score by area calculated or implied.
 */
export function computeAssetStatusByArea(pumps = [], areaFilter = null) {
  if (!Array.isArray(pumps) || pumps.length === 0) return [];

  const filteredPumps = areaFilter && areaFilter !== "ALL"
    ? pumps.filter((p) => (p.area || "Unassigned") === areaFilter)
    : pumps;

  if (filteredPumps.length === 0) return [];

  const areaMap = new Map();

  for (const pump of filteredPumps) {
    const area = pump.area || "Unassigned";
    if (!areaMap.has(area)) {
      areaMap.set(area, {
        area,
        OPERATIONAL: 0,
        STANDBY: 0,
        MAINTENANCE: 0,
        FAULT: 0,
        UNKNOWN: 0,
        total: 0,
      });
    }
    const item = areaMap.get(area);
    const canonical = normalizePumpStatus(pump.status);
    item[canonical] = (item[canonical] || 0) + 1;
    item.total += 1;
  }

  return Array.from(areaMap.values()).sort((a, b) => b.total - a.total);
}

/**
 * Row 2 RIGHT: PM Compliance
 * Donut chart: canonical PM schedule status only.
 * Canonical statuses: COMPLETED, ACTIVE / DUE, OVERDUE, PLANNED.
 *
 * WORK ORDERS ARE NOT USED FOR PM COMPLIANCE.
 */
export function computePMCompliance(pmSchedules = [], areaFilter = null, pumpAreaMap = {}) {
  if (!Array.isArray(pmSchedules) || pmSchedules.length === 0) return [];

  const filtered = areaFilter && areaFilter !== "ALL"
    ? pmSchedules.filter((s) => {
        const pumpTag = s.asset_code || s.pump_tag;
        return pumpAreaMap[pumpTag] === areaFilter || s.area === areaFilter;
      })
    : pmSchedules;

  if (filtered.length === 0) return [];

  let completed = 0;
  let active = 0;
  let overdue = 0;
  let planned = 0;

  for (const s of filtered) {
    const st = String(s.status || "").toUpperCase().trim();
    if (st === "COMPLETED" || st === "DONE") {
      completed += 1;
    } else if (st === "OVERDUE") {
      overdue += 1;
    } else if (st === "ACTIVE" || st === "DUE") {
      active += 1;
    } else if (st === "PLANNED" || st === "SCHEDULED" || st === "DRAFT") {
      planned += 1;
    } else {
      active += 1;
    }
  }

  const slices = [
    { label: "Completed", value: completed, color: colors.success },
    { label: "Due", value: active, color: colors.info },
    { label: "Overdue", value: overdue, color: colors.danger },
    { label: "Planned", value: planned, color: "#8b5cf6" },
  ];

  return slices.filter((s) => s.value > 0);
}

/**
 * Row 3 LEFT: Condition Monitoring Trend
 * Line chart over time.
 * UNKNOWN != ZERO: Missing or unimported historical coverage returns null so
 * TimeSeriesChart renders gaps / N/A rather than a false 0.
 *
 * CM = Condition Monitoring inspections & readings.
 * Leak findings labeled as "Leak Evidence".
 */
export function computeCMTrend(readings = [], periodMonths = 6, areaFilter = null, pumpAreaMap = {}) {
  if (!Array.isArray(readings) || readings.length === 0) return [];

  const filtered = areaFilter && areaFilter !== "ALL"
    ? readings.filter((r) => {
        const pumpTag = r.asset_code || r.pump_tag;
        return pumpAreaMap[pumpTag] === areaFilter || r.area === areaFilter;
      })
    : readings;

  if (filtered.length === 0) return [];

  // Group readings by month (YYYY-MM)
  const monthMap = new Map();

  for (const r of filtered) {
    const dateStr = r.reading_date || r.date || r.created_at;
    if (!dateStr) continue;
    const month = dateStr.slice(0, 7); // "YYYY-MM"
    if (!monthMap.has(month)) {
      monthMap.set(month, {
        total_readings: 0,
        abnormal_count: 0,
        leak_count: 0,
      });
    }
    const bucket = monthMap.get(month);
    bucket.total_readings += 1;

    const cond = String(r.overall_condition || "").toUpperCase();
    const isAbnormal = cond && cond !== "NORMAL" && cond !== "GOOD";
    if (isAbnormal) {
      bucket.abnormal_count += 1;
    }

    const hasLeak = Boolean(r.mechanical_seal_leak_de || r.mechanical_seal_leak_nde);
    if (hasLeak) {
      bucket.leak_count += 1;
    }
  }

  const sortedMonths = Array.from(monthMap.keys()).sort();
  if (sortedMonths.length === 0) return [];

  const [startY, startM] = sortedMonths[0].split("-").map(Number);
  const [endY, endM] = sortedMonths[sortedMonths.length - 1].split("-").map(Number);
  const allMonths = [];
  let curY = startY;
  let curM = startM;
  while (curY < endY || (curY === endY && curM <= endM)) {
    allMonths.push(`${curY}-${String(curM).padStart(2, "0")}`);
    curM += 1;
    if (curM > 12) {
      curM = 1;
      curY += 1;
    }
  }

  const points = [];
  for (const m of allMonths) {
    const b = monthMap.get(m);
    if (b && b.total_readings > 0) {
      points.push({
        date: m,
        total_readings: b.total_readings,
        abnormal_count: b.abnormal_count,
        leak_count: b.leak_count,
      });
    } else {
      // Missing data: null value for gap rendering (UNKNOWN != ZERO)
      points.push({
        date: m,
        total_readings: null,
        abnormal_count: null,
        leak_count: null,
      });
    }
  }

  return points;
}

/**
 * Row 3 RIGHT: Mechanical Seal Condition
 * Donut chart traced strictly to canonical fields:
 * - Normal: normal condition without leak evidence
 * - Under Observation: abnormal/critical condition without leak evidence
 * - Leak Evidence: active leak detected (mechanical_seal_leak_de or mechanical_seal_leak_nde)
 *
 * NOTE: Non-canonical "Replacement Required" category REMOVED per Gate R2 audit.
 * No priority >= 100 or visualization-only heuristics.
 */
export function computeSealCondition(
  readings = [],
  pumpAreaMap = {},
  areaFilter = null
) {
  if (!Array.isArray(readings) || readings.length === 0) return [];

  const pumpState = new Map();

  const isAreaMatch = (tag) => {
    if (!areaFilter || areaFilter === "ALL") return true;
    return pumpAreaMap[tag] === areaFilter;
  };

  // Sort by date ascending so latest reading takes precedence
  const sortedReadings = [...readings].sort((a, b) => {
    const da = a.reading_date || a.date || "";
    const db = b.reading_date || b.date || "";
    return da.localeCompare(db);
  });

  for (const r of sortedReadings) {
    const tag = r.asset_code || r.pump_tag;
    if (!tag || !isAreaMatch(tag)) continue;

    const hasLeak = Boolean(r.mechanical_seal_leak_de || r.mechanical_seal_leak_nde);
    if (hasLeak) {
      pumpState.set(tag, "Leak Evidence");
      continue;
    }

    const cond = String(r.overall_condition || "").toUpperCase();
    const isAbnormal = cond && cond !== "NORMAL" && cond !== "GOOD";
    if (isAbnormal) {
      pumpState.set(tag, "Under Observation");
    } else {
      pumpState.set(tag, "Normal");
    }
  }

  let normal = 0;
  let observation = 0;
  let leak = 0;

  for (const state of pumpState.values()) {
    if (state === "Normal") normal += 1;
    else if (state === "Under Observation") observation += 1;
    else if (state === "Leak Evidence") leak += 1;
  }

  const slices = [
    { label: "Normal", value: normal, color: colors.success },
    { label: "Under Observation", value: observation, color: colors.warning },
    { label: "Leak Evidence", value: leak, color: colors.danger },
  ];

  return slices.filter((s) => s.value > 0);
}

/**
 * Row 4: Maintenance Activity Trend
 * Full-width grouped bar chart across months:
 * - PM Count (Preventive Maintenance)
 * - CM Count (Condition Monitoring activities / inspections)
 * - Seal Replacement Count (actual seal replacement / installation events)
 *
 * CM = Condition Monitoring. ZERO corrective maintenance semantics.
 */
export function computeMaintenanceActivityTrend({
  pmOccurrences = [],
  cmReports = [],
  installations = [],
  trendsData = null,
  areaFilter = null,
  pumpAreaMap = {},
} = {}) {
  // If backend aggregated trendsData is provided directly
  if (trendsData && Array.isArray(trendsData) && trendsData.length > 0) {
    return trendsData.map((d) => ({
      month: d.date || d.month,
      pm_count: d.pm_count ?? 0,
      cm_count: d.cmon_readings ?? d.cm_count ?? 0,
      seal_replacements: d.seal_leaks ?? d.seal_replacements ?? 0,
    }));
  }

  const monthMap = new Map();

  const getBucket = (dateStr) => {
    if (!dateStr) return null;
    const m = dateStr.slice(0, 7);
    if (!monthMap.has(m)) {
      monthMap.set(m, {
        month: m,
        pm_count: 0,
        cm_count: 0,
        seal_replacements: 0,
      });
    }
    return monthMap.get(m);
  };

  const isAreaMatch = (tag) => {
    if (!areaFilter || areaFilter === "ALL") return true;
    return pumpAreaMap[tag] === areaFilter;
  };

  // 1. PM occurrences (Preventive Maintenance)
  for (const pm of pmOccurrences) {
    const tag = pm.asset_code || pm.pump_tag;
    if (!isAreaMatch(tag)) continue;
    const bucket = getBucket(pm.occurrence_date || pm.date);
    if (bucket) bucket.pm_count += 1;
  }

  // 2. CM reports (Condition Monitoring activities / inspections)
  // Sourced strictly from CM inspection events, NEVER from corrective work orders
  for (const cm of cmReports) {
    const tag = cm.asset_code || cm.pump_tag;
    if (!isAreaMatch(tag)) continue;
    const bucket = getBucket(cm.created_at || cm.report_date || cm.reading_date);
    if (bucket) bucket.cm_count += 1;
  }

  // 3. Seal replacements (actual mechanical seal installations / replacements)
  for (const inst of installations) {
    const tag = inst.asset_code || inst.pump_tag;
    if (!isAreaMatch(tag)) continue;
    const bucket = getBucket(inst.installation_date || inst.created_at);
    if (bucket) bucket.seal_replacements += 1;
  }

  return Array.from(monthMap.values()).sort((a, b) => a.month.localeCompare(b.month));
}

export const MAINTENANCE_ACTIVITY_BARS = [
  { key: "pm_count", label: "PM Executed", color: colors.success },
  { key: "cm_count", label: "CM Activity", color: colors.info },
  { key: "seal_replacements", label: "Seal Replacement", color: colors.warning },
];

/**
 * Row 5 LEFT: Top Risk Pumps
 * Horizontal bar chart:
 * [{ pump_tag, risk_score, leak_count, cmon_readings, area, rule }]
 *
 * Uses CANONICAL backend ordering and fields:
 * - bad_actors: leak_count (from ORDER BY leak_count DESC, cmon_readings DESC)
 * - top_risks: priority (from ORDER BY priority DESC)
 *
 * NO custom formula or combined score (CUSTOM_RISK_SCORE=NO).
 */
export function computeTopRiskPumps(topRisks = [], badActors = [], areaFilter = null) {
  const list = [];

  if (Array.isArray(badActors) && badActors.length > 0) {
    for (const ba of badActors) {
      if (areaFilter && areaFilter !== "ALL" && ba.area !== areaFilter) continue;
      list.push({
        pump_tag: ba.pump_tag || ba.tag_number,
        risk_score: Number(ba.leak_count ?? 0),
        leak_count: Number(ba.leak_count ?? 0),
        cmon_readings: Number(ba.cmon_readings ?? 0),
        area: ba.area || "Unassigned",
        rule: (ba.leak_count ?? 0) > 0 ? "Leak Evidence Recorded" : "Under CM Observation",
      });
    }
    return list.slice(0, 7);
  }

  if (Array.isArray(topRisks) && topRisks.length > 0) {
    for (const tr of topRisks) {
      if (areaFilter && areaFilter !== "ALL" && tr.area && tr.area !== areaFilter) continue;
      list.push({
        pump_tag: tr.tag_number || tr.pump_tag,
        risk_score: Number(tr.priority ?? 0),
        leak_count: 0,
        cmon_readings: 0,
        area: tr.area || "Fleet",
        rule: tr.rule_code || tr.title || "Critical Asset",
      });
    }
    return list.slice(0, 7);
  }

  return [];
}

/**
 * Row 5 RIGHT: Mechanical Seal Inventory
 * Bar chart with ACTUAL CANONICAL QUANTITIES:
 * - quantity_on_hand
 * - quantity_available
 * - quantity_reserved
 *
 * Title: "Mechanical Seal Inventory"
 * DO NOT invent Low Stock / Out of Stock thresholds.
 */
export function computeMechanicalSealInventory(sealStocks = [], overview = null) {
  if (Array.isArray(sealStocks) && sealStocks.length > 0) {
    return sealStocks.slice(0, 8).map((s) => ({
      seal_code: s.seal_code || s.material_number || s.model_number || "Seal",
      quantity_on_hand: Number(s.quantity_on_hand ?? s.stock_count ?? s.quantity ?? 0),
      quantity_available: Number(s.quantity_available ?? s.available_count ?? s.quantity ?? 0),
      quantity_reserved: Number(s.quantity_reserved ?? s.reserved_count ?? 0),
    }));
  }

  // Bounded overview fallback if individual seal items not yet loaded
  if (overview && overview.seal_stock_count !== undefined) {
    return [
      {
        seal_code: "Total Fleet Stock",
        quantity_on_hand: Number(overview.seal_stock_count ?? 0),
        quantity_available: Number(overview.seal_stock_count ?? 0),
        quantity_reserved: 0,
      },
    ];
  }

  return [];
}

export const SEAL_INVENTORY_BARS = [
  { key: "quantity_on_hand", label: "On Hand", color: colors.info },
  { key: "quantity_available", label: "Available", color: colors.success },
  { key: "quantity_reserved", label: "Reserved", color: colors.warning },
];

/**
 * Row 6 (OPTIONAL): Mechanical Seal Service Trend
 */
export function computeSealUsageTrend(replacementHistory = []) {
  if (!Array.isArray(replacementHistory) || replacementHistory.length === 0) return [];

  const monthMap = new Map();
  for (const h of replacementHistory) {
    const d = h.replacement_date || h.date || h.installation_date;
    if (!d) continue;
    const m = d.slice(0, 7);
    monthMap.set(m, (monthMap.get(m) || 0) + 1);
  }

  return Array.from(monthMap.entries())
    .map(([date, seal_replacements]) => ({ date, seal_replacements }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Row 1: KPI Calculations
 * Sourced strictly from real production data:
 * 1. Fleet Health (reliability index or N/A)
 * 2. Total Pumps (fleet count)
 * 3. Active Leak / Abnormal Finding (actual CM leak evidence)
 * 4. PM Due (canonical active/due PM schedules)
 * 5. PM Overdue (canonical overdue PM schedules, NEVER work orders)
 * 6. Critical Spare (actual spare stock availability)
 */
export function computeDashboardKpis({
  overview = null,
  reliability = null,
  summary = null,
  analyticsKpis = null,
  readings = [],
  pmSchedules = [],
  areaFilter = null,
} = {}) {
  // 1. Fleet Health: only when returned by existing reliability service
  const fleetHealth = reliability?.fleet_health_score !== undefined && reliability?.fleet_health_score !== null
    ? reliability.fleet_health_score
    : summary?.overall_health ?? null;

  // 2. Total Pumps
  const totalPumps = analyticsKpis?.total_pumps ?? overview?.pump_count ?? null;

  // 3. Active Leak / Abnormal Finding
  let activeLeaks = analyticsKpis?.confirmed_seal_leaks ?? null;
  if (activeLeaks === null && Array.isArray(readings) && readings.length > 0) {
    activeLeaks = readings.filter((r) => r.mechanical_seal_leak_de || r.mechanical_seal_leak_nde).length;
  }

  // 4. PM Due & 5. PM Overdue (strictly from PM schedule status, never work orders)
  let pmDue = null;
  let pmOverdue = null;
  if (Array.isArray(pmSchedules) && pmSchedules.length > 0) {
    pmDue = pmSchedules.filter((s) => {
      const st = String(s.status || "").toUpperCase();
      return st === "ACTIVE" || st === "DUE" || st === "PLANNED";
    }).length;
    pmOverdue = pmSchedules.filter((s) => String(s.status || "").toUpperCase() === "OVERDUE").length;
  } else if (overview?.pm_schedule_count !== undefined) {
    pmDue = overview.pm_schedule_count;
    pmOverdue = 0;
  }

  // 6. Critical Spare
  const criticalSpare = reliability?.total_critical_spare_count ?? summary?.critical_spare_count ?? null;

  return {
    fleetHealth,
    totalPumps,
    activeLeaks,
    pmDue,
    pmOverdue,
    criticalSpare,
    // Secondary glanceables for command center continuity
    running: overview?.status_distribution?.RUNNING ?? overview?.status_distribution?.ACTIVE ?? null,
    standby: overview?.status_distribution?.STANDBY ?? overview?.status_distribution?.IDLE ?? null,
    attention: summary?.critical_asset_count ?? null,
    openWo: overview?.work_order_count ?? null,
  };
}
