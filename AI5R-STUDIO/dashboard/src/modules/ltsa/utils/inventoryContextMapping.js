import { getPumpSpareParts } from "../../../api/ai5rClient";

/**
 * API-to-Inventory-Context-UI field mapping (MWO-INV-CTX-001): seal_code ->
 * sealCode, part_name -> partName, quantity_on_hand -> availability,
 * reorder_point -> minimumStock, location maps directly. Engineering
 * context only -- no editing, no inventory transaction, so this file has
 * no create/update counterpart, unlike pmMapping.js/cmMapping.js.
 *
 * availability/minimumStock are left null when the backend has no
 * seal_stock row for a compatible seal -- never defaulted to 0, since
 * "unknown stock" and "confirmed zero stock" are not the same fact
 * (maintenance_intelligence_service.get_pump_spare_parts's own
 * discipline).
 */
export function mapSparePartRecord(record) {
  return {
    sealCode: record.seal_code,
    partName: record.part_name,
    availability: record.quantity_on_hand,
    minimumStock: record.reorder_point,
    location: record.location,
  };
}

/**
 * Resolves `spareParts` from the canonical API (MWO-INV-CTX-001) for one
 * already-mapped pump. Lazy, not called for the whole list -- mirrors
 * withResolvedLastPM's convention: PumpRegistryTable.jsx doesn't render
 * spare parts, only PumpDetailPanel.jsx does, so this is resolved only
 * for the selected pump. Never throws -- a failed lookup leaves
 * spareParts at its safe default ([]), never fabricated.
 */
export async function withResolvedSpareParts(pump) {
  try {
    const result = await getPumpSpareParts(pump.tag);
    return { ...pump, spareParts: (result?.spare_parts ?? []).map(mapSparePartRecord) };
  } catch {
    return pump;
  }
}
