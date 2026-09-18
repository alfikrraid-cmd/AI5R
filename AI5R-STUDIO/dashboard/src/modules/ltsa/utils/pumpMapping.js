import { getPumpLastPM, getPumpOpenWorkOrders } from "../../../api/ai5rClient";

function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  return String(value).slice(0, 10);
}

/**
 * API-to-Pump-UI field mapping (APP-PUMP-002, per ADR-PUMP-001):
 * tag_number -> code/tag, pump_type -> type, seal_type -> seal,
 * name/criticality map directly (owned Pump attributes since WO-PUMP-002).
 * api_plan -> apiPlan: already stored on ltsa_pumps since WO-PUMP-002, but
 * never previously surfaced here (DISCOVERY-LTSA-REPORT-001's disclosed
 * gap) -- added under APP-ASSET360-001, since Asset 360's Identity zone
 * is its first consumer (ADR-ASSET360-001 Decision table).
 *
 * healthScore, availability, nextPM, recommendation are left null -- each
 * is a future Analytics/AI Capability or still Derived-but-blocked per
 * ADR-PUMP-001, never fabricated. runtimeHours/knowledgeLinks default to
 * 0/[] instead of null -- PumpDetailPanel.jsx calls unguarded
 * `.toLocaleString()`/`.length` on them, so this is defensive typing only,
 * not a business-data decision (ADR-PUMP-001's own distinction).
 * openWO/lastPM default here and are resolved separately (both Derived and
 * real, per WO-PUMP-003/WO-PUMP-004 and ADR-PUMP-002), never fabricated.
 *
 * MWO-PUMP-REGISTRY-N1-REMOVAL-R1 -- openWO's default changed from the
 * literal `0` to `null` (rendered "N/A" by PumpRegistryTable.jsx). `0`
 * presented an unresolved/never-checked Work Order state as a confirmed
 * "zero open work orders" fact -- exactly the fabrication this MWO's own
 * "unknown must never be represented as confirmed 0" rule forbids, made
 * concrete now that the Pump registry's initial load no longer calls
 * withResolvedOpenWO() at all (see Pump.jsx) and the Work Order n8n LIST
 * workflow isn't deployed regardless. withResolvedOpenWO() itself is
 * kept, unused by the registry's initial load, for a future Work Order
 * MWO to re-wire (bulk or lazy) once real data exists.
 *
 * spareParts defaults to [] and is resolved separately too (real, per
 * MWO-INV-CTX-001 / withResolvedSpareParts in inventoryContextMapping.js),
 * same lazy-on-selection convention as lastPM.
 */
export function mapPumpRecord(record) {
  return {
    code: record.tag_number,
    tag: record.tag_number,
    name: record.name,
    manufacturer: record.manufacturer,
    type: record.pump_type,
    seal: record.seal_type,
    apiPlan: record.api_plan,
    location: record.location,
    area: record.area,
    criticality: record.criticality,
    status: record.status,
    healthScore: null,
    availability: null,
    runtimeHours: 0,
    lastPM: null,
    nextPM: null,
    openWO: null,
    recommendation: null,
    knowledgeLinks: [],
    spareParts: [],
  };
}

/**
 * Resolves `openWO` from the Work Order API (WO-PUMP-003) for one
 * already-mapped pump. Never throws -- a failed lookup leaves openWO at
 * its safe default (null/"N/A", per this file's own header comment)
 * rather than failing the whole list for one row. Not called by the Pump
 * registry's initial load any more (MWO-PUMP-REGISTRY-N1-REMOVAL-R1) --
 * kept for a future Work Order MWO's reuse.
 */
export async function withResolvedOpenWO(pump) {
  try {
    const result = await getPumpOpenWorkOrders(pump.tag);
    return { ...pump, openWO: result?.openWO ?? null };
  } catch {
    return pump;
  }
}

/**
 * Resolves `lastPM` from the canonical API (WO-PUMP-004, per ADR-PUMP-002)
 * for one already-mapped pump. Lazy, not called for the whole list --
 * PumpRegistryTable.jsx doesn't render lastPM at all, only
 * PumpDetailPanel.jsx does, so this is resolved only for the selected
 * pump (mirroring how Work Order's timeline is resolved only on
 * selection, not per row). Never throws -- a failed lookup leaves
 * lastPM at its safe default (null), never fabricated.
 */
export async function withResolvedLastPM(pump) {
  try {
    const result = await getPumpLastPM(pump.tag);
    return { ...pump, lastPM: formatDateOnly(result?.last_pm?.performed_at) };
  } catch {
    return pump;
  }
}
