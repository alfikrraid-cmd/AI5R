/**
 * MWO-LTSA-041 -- API-to-Seal-UI field mapping, mirroring pumpMapping.js's
 * mapPumpRecord convention exactly: seal_code -> code, seal_name -> name,
 * manufacturer/status map directly (real seal_registry columns).
 *
 * type is left null -- seal_registry (CANONICAL_SCHEMA.sql) has no direct
 * "type" column; model/material exist but mapping either into "type"
 * would be a semantic guess presented as fact, not a real one, so it is
 * left null per this codebase's "never fabricate" discipline
 * (pumpMapping.js's own precedent for healthScore/availability/
 * recommendation) rather than silently repurposing a different real
 * column under a mismatched label.
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
    name: record.seal_name,
    type: null,
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

/**
 * LTSA_MECHANICAL_SEAL_UNIFIED_IMPLEMENTATION_R1 -- Formats complete seal stock with explicit units.
 * Never outputs naked numbers.
 * When hasStockRecord is false -> "N/A" (unmanaged/unknown).
 * When quantity is null/undefined -> "Unknown".
 * When quantity is 0 -> "0 sets".
 * When quantity is 1 -> "1 set".
 * When quantity > 1 -> "N sets".
 */
export function formatAvailableStock(quantity, hasStockRecord = true) {
  if (!hasStockRecord) return "N/A";
  if (quantity == null) return "Unknown";
  const num = Number(quantity);
  if (isNaN(num)) return "Unknown";
  if (num <= 0) return "0 sets";
  if (num === 1) return "1 set";
  return `${num} sets`;
}

/**
 * Formats compatible pump count with explicit units. Never outputs naked numbers.
 * E.g., "19 pumps", "2 pumps", "1 pump", "0 pumps".
 */
export function formatCompatiblePumps(pumps) {
  const count = Array.isArray(pumps) ? pumps.length : typeof pumps === "number" ? pumps : 0;
  if (count === 1) return "1 pump";
  return `${count} pumps`;
}

/**
 * Parses drawing reference string into individual drawing references.
 * Splits by comma, semicolon, or slash with surrounding spaces.
 */
export function parseDrawingReferences(drawingRef) {
  if (!drawingRef || typeof drawingRef !== "string") return [];
  return drawingRef
    .split(/[,;]|\s+\/\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Compact drawing summary formatter.
 * If drawing has <= 2 references: displays literal text (e.g. "E12893 / E13062", "GA-187530").
 * If drawing has > 2 references: displays count e.g. "4 drawings", "13 drawings".
 */
export function formatDrawingSummary(drawingRef) {
  if (!drawingRef) return "—";
  const parts = parseDrawingReferences(drawingRef);
  if (parts.length > 2) {
    return `${parts.length} drawings`;
  }
  return drawingRef;
}

/**
 * Normalizes an arbitrary string (seal type, shaft size, etc.) into a canonical UPPERCASE slug.
 * Strips whitespace preceding units (e.g. "2 3/4\"" -> "2-3-4") and replaces non-alphanumeric chars with "-".
 */
export function normalizeSealSlug(value) {
  if (value == null) return "UNSPEC";
  const str = String(value);
  const cleaned = str.replace(/\s+(mm|in|"|')/gi, "$1");
  const slug = cleaned.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug || "UNSPEC";
}

/**
 * Builds canonical seal code: LTSA-SEAL-{SEAL_TYPE}-{SHAFT_SIZE}
 */
export function buildCanonicalSealCode(sealType, shaftSize) {
  return `LTSA-SEAL-${normalizeSealSlug(sealType)}-${normalizeSealSlug(shaftSize)}`;
}

/**
 * Matches a stock configuration pool with an authoritative registry seal.
 * Strict join rule: both normalized seal type AND normalized shaft size MUST match.
 * Never match by seal type alone without size.
 * Unknown and Mixed pools are excluded from matching (remain stock-only rows).
 */
export function matchRegistrySeal(pool, registrySeals = []) {
  if (!pool || !registrySeals || !registrySeals.length) return null;
  const sealType = pool.seal_type || "UNKNOWN";
  if (sealType === "MIXED" || sealType === "UNKNOWN") {
    return null;
  }
  const size = pool.nominal_size || pool.physical_stock_size || pool.size || null;
  if (!size) {
    return null;
  }

  // 1. Direct match by pool.seal_code if present
  if (pool.seal_code) {
    const direct = registrySeals.find((s) => s.code === pool.seal_code);
    if (direct) return direct;
  }

  // 2. Exact match by canonical code: LTSA-SEAL-{TYPE}-{SIZE}
  const canonicalCode = buildCanonicalSealCode(sealType, size);
  const byCanonical = registrySeals.find((s) => s.code === canonicalCode);
  if (byCanonical) {
    return byCanonical;
  }

  // 3. Fallback: both normalized type AND normalized size must match
  const typeSlug = normalizeSealSlug(sealType);
  const sizeSlug = normalizeSealSlug(size);
  if (typeSlug === "UNSPEC" || sizeSlug === "UNSPEC") {
    return null;
  }

  return registrySeals.find((s) => {
    const sTypeSlug = normalizeSealSlug(s.name || s.type);
    const sSizeSlug = normalizeSealSlug(s.shaftSize || s.nominal_size || s.size);
    if (sTypeSlug !== typeSlug) return false;
    return sSizeSlug === sizeSlug || s.code === canonicalCode;
  }) ?? null;
}

/**
 * LTSA_MECHANICAL_SEAL_UNIFIED_IMPLEMENTATION_R1
 * Unifies SEAL REGISTRY (authoritative universe of registered seals)
 * and STOCK CONFIGURATION POOLS (inventory/configuration records).
 *
 * Guarantees:
 * 1. Preserves identity granularity keyed by stock_pool_id so collisions
 *    (e.g. T8B1 2-3/4" Pools 9 & 10, T48MP 1-1/4" Pools 36 & 38) remain separate rows.
 * 2. Preserves MIXED pool as VERIFY_CONFIGURATION, not normalized to a seal type.
 * 3. Registered seals with no stock pool remain visible with Available Stock = "N/A".
 * 4. Explicit 0 stock displays as "0 sets"; unknown stock displays as "Unknown".
 */
export function buildUnifiedSealConfigurations(
  registrySeals = [],
  stockPools = [],
  compatibilityRecords = [],
  stockRecords = []
) {
  const stockByCode = new Map((stockRecords || []).map((r) => [r.seal_code, r]));

  const compatBySealCode = new Map();
  (compatibilityRecords || []).forEach((rec) => {
    if (!rec.seal_code) return;
    if (!compatBySealCode.has(rec.seal_code)) {
      compatBySealCode.set(rec.seal_code, []);
    }
    compatBySealCode.get(rec.seal_code).push(rec.pump_tag_number);
  });

  const unifiedList = [];
  const matchedRegistryCodes = new Set();

  // Process Stock Configuration Pools (44 Stock V1 pools)
  (stockPools || []).forEach((pool, index) => {
    const poolId = pool.stock_pool_id != null ? pool.stock_pool_id : `pool-${index + 1}`;
    const sealType = pool.seal_type || "UNKNOWN";
    const nominalSize = pool.nominal_size || null;
    const physicalStockSize = pool.physical_stock_size || null;
    const size = nominalSize || physicalStockSize || "—";
    const quantityOnHand = pool.quantity_on_hand ?? null;
    const quantityAvailable = pool.quantity_available ?? quantityOnHand;
    const drawingRef = pool.drawing_reference || null;
    const verificationStatus = pool.verification_status || "UNKNOWN";
    const location = pool.stock_location || null;
    const gpn = pool.complete_seal_gpn || null;
    const applications = pool.applications || [];
    const appPumps = applications.map((a) => a.equipment_tag).filter(Boolean);

    // Look for matching registry seal using strict type + size matching
    const matchedSeal = matchRegistrySeal(pool, registrySeals);
    if (matchedSeal) {
      matchedRegistryCodes.add(matchedSeal.code);
    }

    const sealCode = matchedSeal?.code || pool.seal_code || (pool.stock_pool_id != null ? `MSSP-${pool.stock_pool_id}` : sealType);
    const sealName = matchedSeal?.name || sealType;
    const allPumps = Array.from(
      new Set([...appPumps, ...(matchedSeal?.compatiblePumps || []), ...(compatBySealCode.get(sealCode) || [])])
    );

    unifiedList.push({
      id: `MSSP-${poolId}`,
      stock_pool_id: pool.stock_pool_id ?? poolId,
      code: sealCode,
      name: sealName,
      seal_type: sealType,
      type: matchedSeal?.type ?? null,
      manufacturer: matchedSeal?.manufacturer ?? (sealType === "MIXED" ? "Various" : "John Crane"),
      model: matchedSeal?.model ?? null,
      nominal_size: nominalSize,
      physical_stock_size: physicalStockSize,
      size,
      shaftSize: matchedSeal?.shaftSize ?? nominalSize,
      material: matchedSeal?.material ?? null,
      temperatureLimit: matchedSeal?.temperatureLimit ?? null,
      pressureLimit: matchedSeal?.pressureLimit ?? null,
      quantity_on_hand: quantityOnHand,
      quantity_reserved: pool.quantity_reserved ?? 0,
      quantity_available: quantityAvailable,
      hasStockRecord: true,
      availableLabel: formatAvailableStock(quantityAvailable, true),
      drawing_reference: drawingRef,
      drawingSummary: formatDrawingSummary(drawingRef),
      stock_location: location,
      verification_status: verificationStatus,
      compatibility_status: pool.compatibility_status || null,
      complete_seal_gpn: gpn,
      gpnJohnCrane: matchedSeal?.gpnJohnCrane ?? gpn,
      kimapPertamina: matchedSeal?.kimapPertamina ?? null,
      status: verificationStatus,
      operationalStatus: matchedSeal?.status ?? null,
      applications,
      compatiblePumps: allPumps,
      compatiblePumpsLabel: formatCompatiblePumps(allPumps),
      compatibleSeals: matchedSeal?.compatibleSeals ?? [],
      recommendation: matchedSeal?.recommendation ?? null,
      knowledgeLinks: matchedSeal?.knowledgeLinks ?? [],
    });
  });

  // Process remaining registered seals (universe of seals without stock pools)
  (registrySeals || []).forEach((seal) => {
    if (matchedRegistryCodes.has(seal.code)) {
      return;
    }

    const stockRec = stockByCode.get(seal.code);
    const hasStockRecord = stockRec != null && stockRec.quantityOnHand != null;
    const quantity = hasStockRecord ? stockRec.quantityOnHand : null;
    const size = seal.shaftSize || "—";
    const pumps = Array.from(
      new Set([...(seal.compatiblePumps || []), ...(compatBySealCode.get(seal.code) || [])])
    );

    unifiedList.push({
      id: seal.code,
      stock_pool_id: null,
      code: seal.code,
      name: seal.name,
      seal_type: seal.type || seal.name || seal.code,
      type: seal.type ?? null,
      manufacturer: seal.manufacturer ?? "Unknown",
      model: seal.model ?? null,
      nominal_size: seal.shaftSize ?? null,
      physical_stock_size: null,
      size,
      shaftSize: seal.shaftSize ?? null,
      material: seal.material ?? null,
      temperatureLimit: seal.temperatureLimit ?? null,
      pressureLimit: seal.pressureLimit ?? null,
      quantity_on_hand: quantity,
      quantity_reserved: 0,
      quantity_available: quantity,
      hasStockRecord,
      availableLabel: formatAvailableStock(quantity, hasStockRecord),
      drawing_reference: null,
      drawingSummary: "—",
      stock_location: stockRec?.location || null,
      verification_status: seal.status || "CONFIRMED",
      compatibility_status: null,
      complete_seal_gpn: seal.gpnJohnCrane ?? null,
      gpnJohnCrane: seal.gpnJohnCrane ?? null,
      kimapPertamina: seal.kimapPertamina ?? null,
      status: seal.status || "ACTIVE",
      operationalStatus: seal.status || "ACTIVE",
      applications: pumps.map((tag) => ({ equipment_tag: tag })),
      compatiblePumps: pumps,
      compatiblePumpsLabel: formatCompatiblePumps(pumps),
      compatibleSeals: seal.compatibleSeals ?? [],
      recommendation: seal.recommendation ?? null,
      knowledgeLinks: seal.knowledgeLinks ?? [],
    });
  });

  return unifiedList;
}

