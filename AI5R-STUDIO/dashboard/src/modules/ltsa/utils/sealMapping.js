/**
 * MWO-LTSA-041 -- API-to-Seal-UI field mapping, mirroring pumpMapping.js's
 * mapPumpRecord convention exactly: seal_code -> code, seal_name -> name,
 * manufacturer/status map directly (real seal_registry columns).
 *
 * MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- type now reads the real
 * seal_type column added by migration 043 (backfilled additively by 044
 * only where an unambiguous source existed). Until this migration runs
 * against a given environment, or for a seal whose seal_type could not
 * be safely backfilled, the API's own SELECT * simply omits/nulls the
 * column, so `?? null` still resolves to the same honest "not yet known"
 * state as before -- this is a widened mapping, not a behavior change
 * for any seal that still has no real value.
 *
 * sealId is the new human-readable identifier (MS-JC-NNNN, migrations
 * 043/044) -- additive alongside `code` (seal_code, still the real
 * business key/PK), never a replacement for it. Also defaults to null:
 * an OEM this migration's mapping does not yet cover (only 'John Crane'
 * is mapped today) is left unassigned rather than guessed.
 *
 * MWO-LTSA-042 -- model, shaftSize, material, temperatureLimit,
 * pressureLimit, createdAt, updatedAt added: all real seal_registry
 * columns (CANONICAL_SCHEMA.sql) that MWO-LTSA-041 left unmapped. Not a
 * repurposing of `type` (which stays null, unchanged) -- these are their
 * own, correctly-named fields, surfaced as the "Lifecycle" card's data
 * source (createdAt/updatedAt = registered/last updated) in
 * SealDetailPanel.jsx.
 *
 * compatiblePumps/compatibleSeals/recommendation/knowledgeLinks default to
 * their safe empty value -- the Compatibility engine and any
 * recommendation/knowledge-link data source are explicitly out of this
 * MWO's scope (per MWO-LTSA-041's "Out of scope" list), never fabricated.
 * compatiblePumps is resolved separately (real, per MWO-LTSA-042 /
 * resolveCompatiblePumps below), same "resolved separately, never
 * fabricated" convention pumpMapping.js's own openWO/lastPM already use.
 *
 * MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- kimapPertamina/gpnJohnCrane
 * (migration 013's own new, nullable seal_registry columns) and
 * createdBy/updatedBy (Record Attribution -- immutable actor UUIDs, never
 * display names). SealOpenDesignView renders updatedBy as the raw user
 * id, not a resolved display name -- a disclosed gap (Phase 8's "resolved
 * user display identity" is not implemented this MWO; doing so would
 * need a new, broadly-readable user-lookup surface this MWO has no
 * evidence is safe to add, given /api/admin/users is admin.users-gated).
 * All four default to null exactly like every other real-but-possibly-
 * absent column above -- an unset identifier is never rendered as
 * anything but an honest "not yet completed" state.
 */
export function mapSealRecord(record) {
  return {
    code: record.seal_code,
    sealId: record.seal_id ?? null,
    name: record.seal_name,
    type: record.seal_type ?? null,
    manufacturer: record.manufacturer,
    model: record.model ?? null,
    shaftSize: record.shaft_size ?? null,
    material: record.material ?? null,
    temperatureLimit: record.temperature_limit ?? null,
    pressureLimit: record.pressure_limit ?? null,
    createdAt: record.created_at ?? null,
    updatedAt: record.updated_at ?? null,
    kimapPertamina: record.kimap_pertamina ?? null,
    gpnJohnCrane: record.gpn_john_crane ?? null,
    createdBy: record.created_by ?? null,
    updatedBy: record.updated_by ?? null,
    status: record.status,
    compatiblePumps: [],
    compatibleSeals: [],
    recommendation: null,
    knowledgeLinks: [],
  };
}

/**
 * MWO-LTSA-042 -- real seal_pump_compatibility record
 * (BP-SEAL-PUMP-COMPATIBILITY/DATABASE/001_create_table.sql: seal_code,
 * pump_tag_number, notes, created_at). pump_tag_number is already a real
 * pump tag (not a code needing translation), unlike sampleSeals.js's
 * fixture data (which uses samplePumps.js's "code" convention) -- see
 * resolveAssetCode's own comment in Seal.jsx for how both are reconciled
 * without changing existing test behavior.
 *
 * Pure, synchronous derivation -- compatibilityRecords is fetched once
 * (getSealCompatibility(), the same real endpoint MWO-LTSA-041 already
 * wired), not re-fetched per seal; this just filters the already-fetched
 * list. Mirrors filteredSeals' own useMemo-over-already-loaded-data
 * pattern in Seal.jsx, not a new data-fetching pattern.
 */
export function resolveCompatiblePumps(sealCode, compatibilityRecords) {
  return compatibilityRecords
    .filter((record) => record.seal_code === sealCode)
    .map((record) => record.pump_tag_number);
}

/**
 * MWO-LTSA-062 -- the exact inverse of resolveCompatiblePumps above, same
 * "resolve once, derive many" pure-function contract, same
 * seal_pump_compatibility record shape. Drawing Workspace uses this to
 * resolve which seal_code(s) are compatible with the pump it's already
 * showing drawings for (Drawing's own real data has no seal_code on the
 * drawing record itself -- see drawingMapping.js's header comment for
 * why this is resolved at the pump level instead of extending the
 * knowledge-endpoint's frozen drawing shape).
 */
export function resolveCompatibleSeals(pumpTagNumber, compatibilityRecords) {
  return compatibilityRecords
    .filter((record) => record.pump_tag_number === pumpTagNumber)
    .map((record) => record.seal_code);
}

/**
 * MWO-LTSA-UI-V2-001 -- Pump Workspace "Seal & Inventory": one merged view
 * replacing the old Compatibility/"Compatible Seals" and Related
 * Engineering/"Inventory" RefGroups, which previously rendered the exact
 * same array twice under two titles. Each lifecycle.relatedEngineering.
 * inventory row (seal_code/quantity_on_hand/location, MWO-LTSA-065) is
 * enriched with the seal's own Type+Size (from `seals`, the already-
 * existing getSeals() endpoint Seal.jsx already fetches -- no new backend
 * route) and its full compatible-pump list (reusing resolveCompatiblePumps
 * above unmodified, over `compatibilityRecords` from getSealCompatibility()
 * -- the same already-existing inverse-relationship utility, not a new
 * resolver).
 *
 * Stock state is exactly quantity_on_hand's own null/0/>0 distinction,
 * already established honestly by the backend (get_pump_spare_parts
 * leaves quantity_on_hand null, never a fabricated zero, when no
 * seal_stock row exists) -- never re-derived here, just labeled. Compatible-
 * pump COUNT is always the seal_pump_compatibility row count
 * (compatiblePumps.length), never quantity_on_hand -- the two are never
 * the same number in this shape, so a caller cannot accidentally conflate
 * "5 compatible pumps" with "5 in stock".
 */
export function buildSealInventoryGroups(inventoryItems, seals, compatibilityRecords) {
  const sealByCode = new Map(seals.map((seal) => [seal.seal_code, seal]));

  return inventoryItems.map((item) => {
    const seal = sealByCode.get(item.seal_code) ?? null;
    const quantity = item.quantity_on_hand ?? null;

    return {
      stockPoolId: item.stock_pool_id ?? null,
      sealCode: item.seal_code ?? null,
      sealName: item.seal_type ?? seal?.seal_name ?? null,
      shaftSize: item.application_size ?? seal?.shaft_size ?? null,
      quantityOnHand: quantity,
      applicationSize: item.application_size ?? null,
      physicalStockSize: item.physical_stock_size ?? null,
      drawingReference: item.drawing_reference ?? null,
      verificationStatus: item.application_verification_status ?? item.verification_status ?? null,
      location: item.stock_location ?? item.location ?? null,
      stockLabel:
        quantity == null ? "Stock Unknown" : quantity > 0 ? `${quantity} sets available` : "Out of Stock",
      availableLabel: quantity == null ? "Stock Unknown" : quantity > 0 ? `${quantity} sets available` : "Out of Stock",
      compatiblePumps: item.equipment_tag ? [item.equipment_tag] : item.seal_code ? resolveCompatiblePumps(item.seal_code, compatibilityRecords) : [],
    };
  });
}

/**
 * MWO-LTSA-042 -- real seal_stock record (BP-SEAL-STOCK/DATABASE/
 * 001_create_table.sql: seal_code, quantity_on_hand, reorder_point,
 * location, created_at, updated_at). null fields stay null (a seal with
 * no seal_stock row has unknown stock, never fabricated as zero) --
 * inventoryContextMapping.js's mapSparePartRecord already established
 * this exact discipline for the equivalent Pump-side concept.
 */
export function mapSealStockRecord(record) {
  return {
    quantityOnHand: record.quantity_on_hand ?? null,
    reorderPoint: record.reorder_point ?? null,
    location: record.location ?? null,
  };
}

/**
 * Pure, synchronous derivation, same rationale as resolveCompatiblePumps
 * above -- stockRecords is fetched once (getSealStock()), this only
 * looks up this one seal's row. Returns null (not a zeroed object) when
 * no seal_stock row exists for this seal -- "no stock record" and
 * "confirmed zero stock" are different facts, never conflated.
 */
export function resolveStock(sealCode, stockRecords) {
  const record = stockRecords.find((item) => item.seal_code === sealCode);
  return record ? mapSealStockRecord(record) : null;
}
