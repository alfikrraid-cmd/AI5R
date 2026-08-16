import { describe, expect, it } from "vitest";
import {
  buildSealInventoryGroups,
  mapSealRecord,
  mapSealStockRecord,
  resolveCompatiblePumps,
  resolveCompatibleSeals,
  resolveStock,
} from "./sealMapping";

// MWO-LTSA-041 -- maps raw seal_registry API fields to the UI shape
// SealRegistryTable.jsx/SealDetailPanel.jsx already expect (code/name/
// type/manufacturer/status/...), mirroring pumpMapping.js's mapPumpRecord
// convention exactly. Fields with no real data source (compatiblePumps,
// compatibleSeals, recommendation, knowledgeLinks -- Compatibility engine
// is explicitly out of this MWO's scope) default to their safe empty
// value, never fabricated.

const RECORD = {
  seal_code: "SC-001",
  seal_name: "John Crane Type 21",
  manufacturer: "John Crane",
  model: "Type 21",
  shaft_size: 45,
  material: "Silicon Carbide",
  temperature_limit: 200,
  pressure_limit: 25,
  status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("mapSealRecord", () => {
  it("maps seal_code to code and seal_name to name", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.code).toBe("SC-001");
    expect(mapped.name).toBe("John Crane Type 21");
  });

  it("maps manufacturer and status directly", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.manufacturer).toBe("John Crane");
    expect(mapped.status).toBe("ACTIVE");
  });

  it("leaves type null -- seal_registry has no direct type column, never guessed", () => {
    // Disclosed judgment call: model/material exist but mapping either
    // into "type" would be a semantic guess, not a real fact -- left null
    // per this codebase's "never fabricate" discipline (pumpMapping.js's
    // own precedent for healthScore/availability/recommendation).
    const mapped = mapSealRecord(RECORD);
    expect(mapped.type).toBeNull();
  });

  it("defaults compatiblePumps/compatibleSeals to empty arrays -- Compatibility engine out of scope", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.compatiblePumps).toEqual([]);
    expect(mapped.compatibleSeals).toEqual([]);
  });

  it("defaults recommendation to null, never fabricated", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.recommendation).toBeNull();
  });

  it("defaults knowledgeLinks to an empty array", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.knowledgeLinks).toEqual([]);
  });

  it("handles a record missing optional fields without throwing", () => {
    const mapped = mapSealRecord({ seal_code: "SC-999", seal_name: "Unnamed" });
    expect(mapped.code).toBe("SC-999");
    expect(mapped.manufacturer).toBeUndefined();
    expect(mapped.status).toBeUndefined();
  });

  // MWO-LTSA-042 -- model/shaftSize/material/temperatureLimit/
  // pressureLimit/createdAt/updatedAt are all real seal_registry columns
  // MWO-LTSA-041 left unmapped (CANONICAL_SCHEMA.sql). Not a repurposing
  // of `type`, which stays null per the test above, unchanged.
  it("maps model, shaftSize, material, temperatureLimit, pressureLimit directly", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.model).toBe("Type 21");
    expect(mapped.shaftSize).toBe(45);
    expect(mapped.material).toBe("Silicon Carbide");
    expect(mapped.temperatureLimit).toBe(200);
    expect(mapped.pressureLimit).toBe(25);
  });

  it("maps createdAt and updatedAt directly -- the Lifecycle card's data source", () => {
    const mapped = mapSealRecord(RECORD);
    expect(mapped.createdAt).toBe("2026-01-01T00:00:00Z");
    expect(mapped.updatedAt).toBe("2026-01-01T00:00:00Z");
  });

  it("defaults the new fields to null when absent, never fabricated", () => {
    const mapped = mapSealRecord({ seal_code: "SC-999", seal_name: "Unnamed" });
    expect(mapped.model).toBeNull();
    expect(mapped.shaftSize).toBeNull();
    expect(mapped.material).toBeNull();
    expect(mapped.temperatureLimit).toBeNull();
    expect(mapped.pressureLimit).toBeNull();
    expect(mapped.createdAt).toBeNull();
    expect(mapped.updatedAt).toBeNull();
  });
});

describe("resolveCompatiblePumps", () => {
  const COMPATIBILITY_RECORDS = [
    { seal_code: "SC-001", pump_tag_number: "211-P-1A", notes: null },
    { seal_code: "SC-001", pump_tag_number: "211-P-1B", notes: null },
    { seal_code: "SC-002", pump_tag_number: "305-P-2", notes: null },
  ];

  it("returns every pump_tag_number for the matching seal_code", () => {
    expect(resolveCompatiblePumps("SC-001", COMPATIBILITY_RECORDS)).toEqual(["211-P-1A", "211-P-1B"]);
  });

  it("returns an empty array when no record matches -- never fabricated", () => {
    expect(resolveCompatiblePumps("SC-999", COMPATIBILITY_RECORDS)).toEqual([]);
  });

  it("does not mutate the input records array", () => {
    const before = JSON.stringify(COMPATIBILITY_RECORDS);
    resolveCompatiblePumps("SC-001", COMPATIBILITY_RECORDS);
    expect(JSON.stringify(COMPATIBILITY_RECORDS)).toBe(before);
  });
});

describe("resolveCompatibleSeals", () => {
  const COMPATIBILITY_RECORDS = [
    { seal_code: "SC-001", pump_tag_number: "211-P-1A", notes: null },
    { seal_code: "SC-002", pump_tag_number: "211-P-1A", notes: null },
    { seal_code: "SC-003", pump_tag_number: "305-P-2", notes: null },
  ];

  it("returns every seal_code compatible with the matching pump_tag_number", () => {
    expect(resolveCompatibleSeals("211-P-1A", COMPATIBILITY_RECORDS)).toEqual(["SC-001", "SC-002"]);
  });

  it("returns an empty array when no record matches -- never fabricated", () => {
    expect(resolveCompatibleSeals("999-X-9", COMPATIBILITY_RECORDS)).toEqual([]);
  });

  it("does not mutate the input records array", () => {
    const before = JSON.stringify(COMPATIBILITY_RECORDS);
    resolveCompatibleSeals("211-P-1A", COMPATIBILITY_RECORDS);
    expect(JSON.stringify(COMPATIBILITY_RECORDS)).toBe(before);
  });
});

// MWO-LTSA-PUMP-SEAL-COMPATIBILITY-001 -- confirms the existing N:N
// seal_pump_compatibility model (composite PK: seal_code, pump_tag_number)
// already satisfies every required Pump<->Seal relationship shape via
// resolveCompatibleSeals/resolveCompatiblePumps, reused unmodified above.
// No new resolver, table, or endpoint -- this block only closes the
// explicit test-scenario list (one pump -> one seal; sister pumps never
// inherit each other's compatibility) that wasn't yet covered as its own
// case. Duplicate-row rejection is a DB-level guarantee (the composite
// PRIMARY KEY itself), already proven by
// PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY/TEST/
// seal_pump_compatibility_create_test.sh -- not re-proven here.
describe("Pump <-> Seal N:N relationship", () => {
  it("one pump -> one seal: a pump with a single compatibility row resolves exactly one seal_code", () => {
    const records = [{ seal_code: "SC-100", pump_tag_number: "101-P-10A", notes: null }];
    expect(resolveCompatibleSeals("101-P-10A", records)).toEqual(["SC-100"]);
  });

  it("one seal -> one pump: the inverse direction of the same single row", () => {
    const records = [{ seal_code: "SC-100", pump_tag_number: "101-P-10A", notes: null }];
    expect(resolveCompatiblePumps("SC-100", records)).toEqual(["101-P-10A"]);
  });

  it("sister pumps (A/B) remain independent -- distinct compatibility, never auto-copied", () => {
    // Real RU II shape: 101-P-10A and 101-P-10B are two distinct physical
    // pumps that happen to share a tag prefix. Their seal compatibility
    // must come only from their own explicit rows, never inferred from
    // the sibling.
    const records = [
      { seal_code: "SC-100", pump_tag_number: "101-P-10A", notes: null },
      { seal_code: "SC-200", pump_tag_number: "101-P-10B", notes: null },
    ];
    expect(resolveCompatibleSeals("101-P-10A", records)).toEqual(["SC-100"]);
    expect(resolveCompatibleSeals("101-P-10B", records)).toEqual(["SC-200"]);
  });

  it("sister pump with no compatibility row of its own resolves empty, never borrows the sibling's seal", () => {
    const records = [{ seal_code: "SC-100", pump_tag_number: "101-P-10A", notes: null }];
    expect(resolveCompatibleSeals("101-P-10B", records)).toEqual([]);
  });
});

describe("mapSealStockRecord", () => {
  it("maps quantity_on_hand, reorder_point, location directly", () => {
    const mapped = mapSealStockRecord({ quantity_on_hand: 12, reorder_point: 4, location: "Warehouse A" });
    expect(mapped.quantityOnHand).toBe(12);
    expect(mapped.reorderPoint).toBe(4);
    expect(mapped.location).toBe("Warehouse A");
  });

  it("defaults missing fields to null, never fabricated as zero", () => {
    const mapped = mapSealStockRecord({});
    expect(mapped.quantityOnHand).toBeNull();
    expect(mapped.reorderPoint).toBeNull();
    expect(mapped.location).toBeNull();
  });
});

describe("resolveStock", () => {
  const STOCK_RECORDS = [
    { seal_code: "SC-001", quantity_on_hand: 12, reorder_point: 4, location: "Warehouse A" },
  ];

  it("returns the mapped stock record for a matching seal_code", () => {
    expect(resolveStock("SC-001", STOCK_RECORDS)).toEqual({
      quantityOnHand: 12,
      reorderPoint: 4,
      location: "Warehouse A",
    });
  });

  it("returns null (not a zeroed object) when no seal_stock row exists -- unknown stock is not zero stock", () => {
    expect(resolveStock("SC-999", STOCK_RECORDS)).toBeNull();
  });
});

// MWO-LTSA-UI-V2-001 -- Pump Workspace "Seal & Inventory": enriches
// lifecycle.relatedEngineering.inventory (seal_code/quantity_on_hand/
// location only) with each seal's real Type/Size and full compatible-pump
// list, replacing the old duplicate Compatibility/"Compatible Seals" and
// Related Engineering/"Inventory" RefGroups that rendered the same array
// twice.
describe("buildSealInventoryGroups", () => {
  const SEALS = [
    { seal_code: "SC-TANDEM", seal_name: "TANDEM SEAL", shaft_size: "55MM" },
    { seal_code: "SC-T48MP", seal_name: "T48MP", shaft_size: "1-3/8\"" },
  ];

  const COMPATIBILITY = [
    { seal_code: "SC-TANDEM", pump_tag_number: "140-P-24A" },
    { seal_code: "SC-TANDEM", pump_tag_number: "140-P-24B" },
    { seal_code: "SC-TANDEM", pump_tag_number: "945-P-7A" },
    { seal_code: "SC-TANDEM", pump_tag_number: "945-P-7B" },
    { seal_code: "SC-TANDEM", pump_tag_number: "945-P-7C" },
    { seal_code: "SC-T48MP", pump_tag_number: "101-P-10B" },
  ];

  it("enriches an inventory row with the seal's real Type+Size", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-TANDEM", quantity_on_hand: null, location: null }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.sealName).toBe("TANDEM SEAL");
    expect(group.shaftSize).toBe("55MM");
  });

  it("compatible-pump count is the full compatibility list, never quantity_on_hand -- the two are never the same number", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-TANDEM", quantity_on_hand: 1, location: null }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.compatiblePumps).toEqual(["140-P-24A", "140-P-24B", "945-P-7A", "945-P-7B", "945-P-7C"]);
    expect(group.compatiblePumps.length).toBe(5);
    expect(group.quantityOnHand).toBe(1);
  });

  it("labels quantity > 0 as Available · N", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-T48MP", quantity_on_hand: 3, location: "Warehouse A" }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.stockLabel).toBe("Available · 3");
  });

  it("labels quantity === 0 as Out of stock · 0, distinct from unknown", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-T48MP", quantity_on_hand: 0, location: "Warehouse A" }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.stockLabel).toBe("Out of stock · 0");
  });

  it("labels a missing stock record (null quantity) as No stock record, never fabricated as zero", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-TANDEM", quantity_on_hand: null, location: null }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.stockLabel).toBe("No stock record");
  });

  it("preserves multiple seals on one pump as independent groups, never collapsed", () => {
    const groups = buildSealInventoryGroups(
      [
        { seal_code: "SC-TANDEM", quantity_on_hand: null, location: null },
        { seal_code: "SC-T48MP", quantity_on_hand: 0, location: "Warehouse A" },
      ],
      SEALS,
      COMPATIBILITY
    );
    expect(groups).toHaveLength(2);
    expect(groups[0].sealCode).toBe("SC-TANDEM");
    expect(groups[1].sealCode).toBe("SC-T48MP");
  });

  it("does not fabricate a seal name when the seal_code has no matching seal_registry record", () => {
    const [group] = buildSealInventoryGroups(
      [{ seal_code: "SC-UNKNOWN", quantity_on_hand: 2, location: null }],
      SEALS,
      COMPATIBILITY
    );
    expect(group.sealName).toBeNull();
    expect(group.shaftSize).toBeNull();
    expect(group.sealCode).toBe("SC-UNKNOWN");
  });
});
