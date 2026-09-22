import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Seal from "./Seal";
import LTSAWorkspace from "./LTSAWorkspace";
import { parseWorkspaceLocation } from "../workspace/WorkspaceRegistry";
import {
  formatAvailableStock,
  formatCompatiblePumps,
  formatDrawingSummary,
  parseDrawingReferences,
  buildUnifiedSealConfigurations,
  normalizeSealSlug,
  buildCanonicalSealCode,
  matchRegistrySeal,
} from "../utils/sealMapping";
import {
  getSeals,
  getSealCompatibility,
  getSealStock,
  getMechanicalSealStock,
  postEngineeringAI,
  getPMSchedules,
  getCMReports,
  getWorkOrders,
  getSealUnits,
  getSealUnitLifecycle,
  getSealUnitInspections,
  getSealUnitRepairs,
  getSealUnitWarranty,
  getSealUnitInstallationReports,
  getSealUnitHistory,
  getPumps,
} from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getSeals: vi.fn(),
  getSealCompatibility: vi.fn(),
  getSealStock: vi.fn(),
  getMechanicalSealStock: vi.fn(),
  postEngineeringAI: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
  getWorkOrders: vi.fn(),
  getSealUnits: vi.fn(),
  getSealUnitLifecycle: vi.fn(),
  getSealUnitInspections: vi.fn(),
  getSealUnitRepairs: vi.fn(),
  getSealUnitWarranty: vi.fn(),
  getSealUnitInstallationReports: vi.fn(),
  getSealUnitHistory: vi.fn(),
  getPumps: vi.fn(),
}));

const MOCK_STOCK_POOLS = [
  // Collision pair 1: T8B1 2-3/4" Pools 9 & 10
  {
    stock_pool_id: 9,
    seal_type: "T8B1",
    nominal_size: '2-3/4"',
    physical_stock_size: '2.750"',
    quantity_on_hand: 1,
    quantity_reserved: 0,
    quantity_available: 1,
    drawing_reference: "E12893 / E13062",
    stock_location: "TAP DMI",
    verification_status: "CONFIRMED",
    compatibility_status: "CONFIRMED",
    applications: [{ equipment_tag: "210-P-1A" }, { equipment_tag: "210-P-1B" }],
  },
  {
    stock_pool_id: 10,
    seal_type: "T8B1",
    nominal_size: '2-3/4"',
    physical_stock_size: '2.750"',
    quantity_on_hand: 4,
    quantity_reserved: 0,
    quantity_available: 4,
    drawing_reference: "MI-8B-1615",
    stock_location: "TAP DMI",
    verification_status: "VERIFY",
    compatibility_status: "VERIFY",
    applications: [{ equipment_tag: "210-P-2A" }],
  },
  // Collision pair 2: T48MP 1-1/4" Pools 36 & 38
  {
    stock_pool_id: 36,
    seal_type: "T48MP",
    nominal_size: '1-1/4"',
    physical_stock_size: '1.250"',
    quantity_on_hand: 1,
    quantity_reserved: 0,
    quantity_available: 1,
    drawing_reference: "E12926",
    stock_location: "TAP DMI",
    verification_status: "CONFIRMED",
    compatibility_status: "CONFIRMED",
    applications: [{ equipment_tag: "300-P-1A" }],
  },
  {
    stock_pool_id: 38,
    seal_type: "T48MP",
    nominal_size: '1-1/4"',
    physical_stock_size: '1.250"',
    quantity_on_hand: 1,
    quantity_reserved: 0,
    quantity_available: 1,
    drawing_reference: "GA-214077",
    stock_location: "TAP DMI",
    verification_status: "CONFIRMED",
    compatibility_status: "CONFIRMED",
    applications: [{ equipment_tag: "300-P-2A" }],
  },
  // Multi-drawing pool (> 2 drawings): e.g. 4 drawings
  {
    stock_pool_id: 15,
    seal_type: "T58B",
    nominal_size: '2"',
    physical_stock_size: '2.000"',
    quantity_on_hand: 3,
    quantity_reserved: 0,
    quantity_available: 3,
    drawing_reference: "GA-187530, GA-187531, GA-187532, GA-187533",
    stock_location: "TAP DMI",
    verification_status: "CONFIRMED",
    compatibility_status: "CONFIRMED",
    applications: [{ equipment_tag: "100-P-1A" }, { equipment_tag: "100-P-1B" }],
  },
  // Zero quantity explicitly recorded
  {
    stock_pool_id: 20,
    seal_type: "T59B",
    nominal_size: '1-1/2"',
    physical_stock_size: '1.500"',
    quantity_on_hand: 0,
    quantity_reserved: 0,
    quantity_available: 0,
    drawing_reference: "E10001",
    stock_location: "TAP DMI",
    verification_status: "CONFIRMED",
    compatibility_status: "CONFIRMED",
    applications: [{ equipment_tag: "100-P-2A" }],
  },
  // Unknown quantity pool
  {
    stock_pool_id: 25,
    seal_type: "T609",
    nominal_size: '3"',
    physical_stock_size: '3.000"',
    quantity_on_hand: null,
    quantity_reserved: 0,
    quantity_available: null,
    drawing_reference: "E10002",
    stock_location: "TAP DMI",
    verification_status: "UNKNOWN",
    compatibility_status: "UNKNOWN",
    applications: [{ equipment_tag: "100-P-3A" }],
  },
  // MIXED pool (Pool 44)
  {
    stock_pool_id: 44,
    seal_type: "MIXED",
    nominal_size: "Various",
    physical_stock_size: null,
    quantity_on_hand: 5,
    quantity_reserved: 0,
    quantity_available: 5,
    drawing_reference: null,
    stock_location: "TAP DMI",
    verification_status: "VERIFY_CONFIGURATION",
    compatibility_status: "VERIFY_CONFIGURATION",
    applications: [],
  },
];

const MOCK_REGISTRY_SEALS = [
  {
    seal_code: "SC-UNMANAGED-1",
    seal_name: "Flowserve ISC2-60",
    manufacturer: "Flowserve",
    status: "ACTIVE",
    shaft_size: '2.5"',
  },
  {
    seal_code: "SC-UNMANAGED-2",
    seal_name: "AESSEAL P8-Cartridge",
    manufacturer: "AESSEAL",
    status: "STANDBY",
    shaft_size: '1.75"',
  },
];

beforeEach(() => {
  postEngineeringAI.mockResolvedValue({
    summary: "Mock AI Summary",
    findings: [],
    confidence: null,
    evidence: [],
    recommendations: [],
    risk: null,
    remaining_life: null,
    provider: "UNKNOWN",
    model: "UNKNOWN",
    latency: 0,
    token_usage: {},
    trace_id: "trace-test",
    execution_status: "SUCCESS",
    source_references: [],
    error: null,
  });
  getSeals.mockResolvedValue(MOCK_REGISTRY_SEALS);
  getSealCompatibility.mockResolvedValue([
    { seal_code: "SC-UNMANAGED-1", pump_tag_number: "500-P-1A" },
  ]);
  getSealStock.mockResolvedValue([]);
  getMechanicalSealStock.mockResolvedValue({
    items: MOCK_STOCK_POOLS,
    total: MOCK_STOCK_POOLS.length,
    total_quantity: 15,
    limit: 100,
    offset: 0,
  });
  getPMSchedules.mockResolvedValue([]);
  getCMReports.mockResolvedValue([]);
  getWorkOrders.mockResolvedValue([]);
  getSealUnits.mockResolvedValue([]);
  getSealUnitLifecycle.mockResolvedValue([]);
  getSealUnitInspections.mockResolvedValue([]);
  getSealUnitRepairs.mockResolvedValue([]);
  getSealUnitWarranty.mockResolvedValue([]);
  getSealUnitInstallationReports.mockResolvedValue([]);
  getSealUnitHistory.mockResolvedValue([]);
  getPumps.mockResolvedValue([]);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("LTSA Mechanical Seal Unified Workspace - Pure Utility Functions", () => {
  it("formatAvailableStock formats units explicitly and never prints naked numbers", () => {
    expect(formatAvailableStock(0, true)).toBe("0 sets");
    expect(formatAvailableStock(1, true)).toBe("1 set");
    expect(formatAvailableStock(3, true)).toBe("3 sets");
    expect(formatAvailableStock(107, true)).toBe("107 sets");
    expect(formatAvailableStock(null, true)).toBe("Unknown");
    expect(formatAvailableStock(undefined, true)).toBe("Unknown");
    expect(formatAvailableStock(null, false)).toBe("N/A");
    expect(formatAvailableStock(5, false)).toBe("N/A");
  });

  it("formatCompatiblePumps formats units explicitly and never prints naked numbers", () => {
    expect(formatCompatiblePumps([])).toBe("0 pumps");
    expect(formatCompatiblePumps(["300-P-1A"])).toBe("1 pump");
    expect(formatCompatiblePumps(["300-P-1A", "300-P-1B"])).toBe("2 pumps");
    expect(formatCompatiblePumps(19)).toBe("19 pumps");
    expect(formatCompatiblePumps(0)).toBe("0 pumps");
  });

  it("parseDrawingReferences splits multiple drawings correctly", () => {
    expect(parseDrawingReferences("GA-187530, GA-187531; GA-187532")).toEqual([
      "GA-187530",
      "GA-187531",
      "GA-187532",
    ]);
    expect(parseDrawingReferences("E12893 / E13062")).toEqual(["E12893", "E13062"]);
    expect(parseDrawingReferences("E12926")).toEqual(["E12926"]);
    expect(parseDrawingReferences(null)).toEqual([]);
  });

  it("formatDrawingSummary displays literal string for <= 2 drawings and count for > 2 drawings", () => {
    expect(formatDrawingSummary("E12926")).toBe("E12926");
    expect(formatDrawingSummary("E12893 / E13062")).toBe("E12893 / E13062");
    expect(formatDrawingSummary("GA-187530, GA-187531, GA-187532, GA-187533")).toBe("4 drawings");
    expect(formatDrawingSummary(null)).toBe("—");
  });

  it("buildUnifiedSealConfigurations preserves collision identity keyed by stock_pool_id", () => {
    const unified = buildUnifiedSealConfigurations(
      MOCK_REGISTRY_SEALS.map((r) => ({
        code: r.seal_code,
        name: r.seal_name,
        manufacturer: r.manufacturer,
        status: r.status,
        shaftSize: r.shaft_size,
      })),
      MOCK_STOCK_POOLS,
      [],
      []
    );

    // T8B1 Pools 9 & 10 must both exist as separate rows
    const pool9 = unified.find((item) => item.stock_pool_id === 9);
    const pool10 = unified.find((item) => item.stock_pool_id === 10);
    expect(pool9).toBeDefined();
    expect(pool10).toBeDefined();
    expect(pool9.id).not.toBe(pool10.id);
    expect(pool9.quantity_available).toBe(1);
    expect(pool10.quantity_available).toBe(4);
    expect(pool9.drawing_reference).toBe("E12893 / E13062");
    expect(pool10.drawing_reference).toBe("MI-8B-1615");

    // T48MP Pools 36 & 38 must both exist as separate rows
    const pool36 = unified.find((item) => item.stock_pool_id === 36);
    const pool38 = unified.find((item) => item.stock_pool_id === 38);
    expect(pool36).toBeDefined();
    expect(pool38).toBeDefined();
    expect(pool36.id).not.toBe(pool38.id);
    expect(pool36.drawing_reference).toBe("E12926");
    expect(pool38.drawing_reference).toBe("GA-214077");

    // MIXED pool must be preserved as VERIFY_CONFIGURATION
    const mixed = unified.find((item) => item.seal_type === "MIXED");
    expect(mixed).toBeDefined();
    expect(mixed.verification_status).toBe("VERIFY_CONFIGURATION");

    // Unmanaged registered seals must have Available Stock = N/A
    const unmanaged1 = unified.find((item) => item.code === "SC-UNMANAGED-1");
    expect(unmanaged1).toBeDefined();
    expect(unmanaged1.availableLabel).toBe("N/A");
    expect(unmanaged1.hasStockRecord).toBe(false);
  });

  it("normalizeSealSlug and buildCanonicalSealCode produce valid UPPERCASE canonical identifiers", () => {
    expect(normalizeSealSlug('2-3/4"')).toBe("2-3-4");
    expect(normalizeSealSlug('1-1/4"')).toBe("1-1-4");
    expect(normalizeSealSlug('139.70MM/130.10MM')).toBe("139-70MM-130-10MM");
    expect(normalizeSealSlug('55 mm')).toBe("55MM");
    expect(normalizeSealSlug(null)).toBe("UNSPEC");
    expect(normalizeSealSlug("")).toBe("UNSPEC");

    expect(buildCanonicalSealCode("T8B1", '2-3/4"')).toBe("LTSA-SEAL-T8B1-2-3-4");
    expect(buildCanonicalSealCode("T48MP", '1-1/4"')).toBe("LTSA-SEAL-T48MP-1-1-4");
    expect(buildCanonicalSealCode("T8-1 DOUBLE", "139.70MM/130.10MM")).toBe(
      "LTSA-SEAL-T8-1-DOUBLE-139-70MM-130-10MM"
    );
  });

  it("matchRegistrySeal matches by normalized seal type AND shaft size with 0 wrong size matches", () => {
    const registrySeals = [
      { code: "LTSA-SEAL-T8B1-1-3-4", name: "T8B1", shaftSize: "1-3/4" },
      { code: "LTSA-SEAL-T8B1-2-3-4", name: "T8B1", shaftSize: "2-3/4" },
      { code: "LTSA-SEAL-T48MP-1-1-4", name: "T48MP", shaftSize: "1-1/4" },
      { code: "LTSA-SEAL-T48MP-2", name: "T48MP", shaftSize: "2" },
    ];

    // Pool 9: T8B1 2-3/4" -> MUST match LTSA-SEAL-T8B1-2-3-4, NOT LTSA-SEAL-T8B1-1-3-4
    const pool9 = { stock_pool_id: 9, seal_type: "T8B1", nominal_size: '2-3/4"' };
    const matched9 = matchRegistrySeal(pool9, registrySeals);
    expect(matched9).toBeDefined();
    expect(matched9.code).toBe("LTSA-SEAL-T8B1-2-3-4");
    expect(matched9.code).not.toBe("LTSA-SEAL-T8B1-1-3-4");

    // Pool 10: T8B1 2-3/4" -> MUST match LTSA-SEAL-T8B1-2-3-4
    const pool10 = { stock_pool_id: 10, seal_type: "T8B1", nominal_size: '2-3/4"' };
    const matched10 = matchRegistrySeal(pool10, registrySeals);
    expect(matched10).toBeDefined();
    expect(matched10.code).toBe("LTSA-SEAL-T8B1-2-3-4");

    // UNKNOWN and MIXED pools MUST return null (unmapped stock-only pools)
    const poolUnknown = { stock_pool_id: 13, seal_type: "UNKNOWN", nominal_size: '2-3/4"' };
    const poolMixed = { stock_pool_id: 39, seal_type: "MIXED", nominal_size: '1-3/4"' };
    expect(matchRegistrySeal(poolUnknown, registrySeals)).toBeNull();
    expect(matchRegistrySeal(poolMixed, registrySeals)).toBeNull();
  });

  it("buildUnifiedSealConfigurations satisfies LTSA_MECHANICAL_SEAL_UNIFIED_JOIN_IDENTITY_FIX_R1 criteria", () => {
    const CANONICAL_REGISTRY_FIXTURE = [
      { code: "LTSA-SEAL-T8B1-1-3-4", name: "T8B1", shaftSize: "1.75", manufacturer: "John Crane", status: "ACTIVE" },
      { code: "LTSA-SEAL-T8B1-2-3-4", name: "T8B1", shaftSize: "2.75", manufacturer: "John Crane", status: "ACTIVE" },
      { code: "LTSA-SEAL-T48MP-1-1-4", name: "T48MP", shaftSize: "1.25", manufacturer: "John Crane", status: "ACTIVE" },
      { code: "LTSA-SEAL-T48MP-2", name: "T48MP", shaftSize: "2.0", manufacturer: "John Crane", status: "ACTIVE" },
      { code: "LTSA-SEAL-REG-ONLY-1", name: "Special Seal", shaftSize: "3.0", manufacturer: "Flowserve", status: "ACTIVE" },
    ];

    const STOCK_POOLS_FIXTURE = [
      {
        stock_pool_id: 9,
        seal_type: "T8B1",
        nominal_size: '2-3/4"',
        quantity_on_hand: 1,
        quantity_available: 1,
        drawing_reference: "E12893 / E13062",
        verification_status: "CONFIRMED",
        applications: [{ equipment_tag: "210-P-1A" }],
      },
      {
        stock_pool_id: 10,
        seal_type: "T8B1",
        nominal_size: '2-3/4"',
        quantity_on_hand: 4,
        quantity_available: 4,
        drawing_reference: "MI-8B-1615",
        verification_status: "VERIFY",
        applications: [{ equipment_tag: "210-P-2A" }],
      },
      {
        stock_pool_id: 36,
        seal_type: "T48MP",
        nominal_size: '1-1/4"',
        quantity_on_hand: 1,
        quantity_available: 1,
        drawing_reference: "E12926",
        verification_status: "CONFIRMED",
        applications: [{ equipment_tag: "300-P-1A" }],
      },
      {
        stock_pool_id: 38,
        seal_type: "T48MP",
        nominal_size: '1-1/4"',
        quantity_on_hand: 1,
        quantity_available: 1,
        drawing_reference: "GA-214077",
        verification_status: "CONFIRMED",
        applications: [{ equipment_tag: "300-P-2A" }],
      },
      {
        stock_pool_id: 13,
        seal_type: "UNKNOWN",
        nominal_size: '2-3/4"',
        quantity_on_hand: 1,
        quantity_available: 1,
        verification_status: "UNKNOWN",
        applications: [],
      },
      {
        stock_pool_id: 39,
        seal_type: "MIXED",
        nominal_size: '1-3/4"',
        quantity_on_hand: 5,
        quantity_available: 5,
        verification_status: "VERIFY_CONFIGURATION",
        applications: [],
      },
    ];

    const unified = buildUnifiedSealConfigurations(
      CANONICAL_REGISTRY_FIXTURE,
      STOCK_POOLS_FIXTURE,
      [],
      []
    );

    // 1. T8B1_POOL_9_REGISTRY = LTSA-SEAL-T8B1-2-3-4
    const pool9 = unified.find((item) => item.stock_pool_id === 9);
    expect(pool9).toBeDefined();
    expect(pool9.code).toBe("LTSA-SEAL-T8B1-2-3-4");

    // 2. T8B1_POOL_10_REGISTRY = LTSA-SEAL-T8B1-2-3-4
    const pool10 = unified.find((item) => item.stock_pool_id === 10);
    expect(pool10).toBeDefined();
    expect(pool10.code).toBe("LTSA-SEAL-T8B1-2-3-4");

    // 3. POOL_9_ROW_PRESERVED and POOL_10_ROW_PRESERVED as separate rows
    expect(pool9.id).toBe("MSSP-9");
    expect(pool10.id).toBe("MSSP-10");
    expect(pool9.id).not.toBe(pool10.id);
    expect(pool9.quantity_available).toBe(1);
    expect(pool10.quantity_available).toBe(4);

    // 4. WRONG_SIZE_MATCHES = 0 (Pool 9 & 10 must NOT match LTSA-SEAL-T8B1-1-3-4)
    expect(pool9.code).not.toBe("LTSA-SEAL-T8B1-1-3-4");
    expect(pool10.code).not.toBe("LTSA-SEAL-T8B1-1-3-4");

    // 5. T48MP Pools 36 & 38 matched correctly and preserved as distinct rows
    const pool36 = unified.find((item) => item.stock_pool_id === 36);
    const pool38 = unified.find((item) => item.stock_pool_id === 38);
    expect(pool36.code).toBe("LTSA-SEAL-T48MP-1-1-4");
    expect(pool38.code).toBe("LTSA-SEAL-T48MP-1-1-4");
    expect(pool36.id).not.toBe(pool38.id);

    // 6. UNKNOWN_POOL_PRESERVED = YES
    const pool13 = unified.find((item) => item.stock_pool_id === 13);
    expect(pool13).toBeDefined();
    expect(pool13.code).toBe("MSSP-13");
    expect(pool13.seal_type).toBe("UNKNOWN");

    // 7. MIXED_POOL_PRESERVED = YES with VERIFY_CONFIGURATION
    const pool39 = unified.find((item) => item.stock_pool_id === 39);
    expect(pool39).toBeDefined();
    expect(pool39.code).toBe("MSSP-39");
    expect(pool39.verification_status).toBe("VERIFY_CONFIGURATION");

    // 8. Registry-only row preserved
    const regOnly = unified.find((item) => item.code === "LTSA-SEAL-REG-ONLY-1");
    expect(regOnly).toBeDefined();
    expect(regOnly.hasStockRecord).toBe(false);
    expect(regOnly.availableLabel).toBe("N/A");
  });
});

describe("LTSA Mechanical Seal Unified Workspace - Component Integration", () => {
  it("renders PageHeader with 'Mechanical Seal' and subtitle", async () => {
    render(<Seal />);
    expect(await screen.findByRole("heading", { name: "Mechanical Seal" })).toBeTruthy();
    expect(screen.getByText("Seal Registry, Compatibility & Inventory")).toBeTruthy();
    // Backward-compatible hidden heading
    expect(screen.getByRole("heading", { name: "Seal Workspace" })).toBeTruthy();
  });

  it("renders the 4 KPI cards with dynamic calculations", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    expect(screen.getByText("Registered Seals")).toBeTruthy();
    expect(screen.getByText("Complete Seal Stock")).toBeTruthy();
    expect(screen.getByText("Compatibility Links")).toBeTruthy();
    expect(screen.getByText("Verification Required")).toBeTruthy();

    // Complete Seal Stock must show "15 sets" (from total_quantity)
    expect(screen.getByText("15 sets")).toBeTruthy();
  });

  it("renders table with explicit pump and stock units", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    // Pool 9 has 2 pumps -> "2 pumps"
    expect(screen.getAllByText("2 pumps").length).toBeGreaterThan(0);

    // Pool 10 has 1 pump -> "1 pump"
    expect(screen.getAllByText("1 pump").length).toBeGreaterThan(0);

    // Pool 20 has 0 stock -> "0 sets"
    expect(screen.getByText("0 sets")).toBeTruthy();

    // Pool 25 has null stock -> "Unknown"
    expect(screen.getByText("Unknown")).toBeTruthy();

    // Unmanaged registry seal -> "N/A"
    expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
  });

  it("renders compact drawing format for > 2 drawings with tooltip", async () => {
    render(<Seal />);
    await screen.findByText("T58B");

    // Pool 15 has 4 drawings -> should display "4 drawings"
    const compactDrawing = screen.getByText("4 drawings");
    expect(compactDrawing).toBeTruthy();
    expect(compactDrawing.getAttribute("title")).toBe(
      "GA-187530, GA-187531, GA-187532, GA-187533"
    );
  });

  it("filters table by search text across seal code, name, size, and drawing", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    const searchBox = screen.getByRole("searchbox");

    // Search by drawing
    fireEvent.change(searchBox, { target: { value: "MI-8B-1615" } });
    expect(screen.getByText("MI-8B-1615")).toBeTruthy();
    expect(screen.queryByText("E12926")).toBeNull();

    // Search by pump tag
    fireEvent.change(searchBox, { target: { value: "300-P-1A" } });
    expect(screen.getByText("E12926")).toBeTruthy();
    expect(screen.queryByText("MI-8B-1615")).toBeNull();
  });

  it("filters table by verification status", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    const statusSelect = screen.getByRole("combobox", { name: /filter by status/i });
    fireEvent.change(statusSelect, { target: { value: "VERIFY_CONFIGURATION" } });

    expect(screen.getByText("MIXED")).toBeTruthy();
    expect(screen.queryByText("E12926")).toBeNull();
  });

  it("filters table by stock availability pill buttons", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    // Click "Out of Stock (0)" pill
    fireEvent.click(screen.getByRole("button", { name: "Out of Stock (0)" }));
    expect(screen.getByText("T59B")).toBeTruthy();
    expect(screen.queryByText("T58B")).toBeNull();

    // Click "All Stock" pill
    fireEvent.click(screen.getByRole("button", { name: "All Stock" }));
    expect(screen.getByText("T58B")).toBeTruthy();
  });

  it("selecting a row displays detail panel with 5 tabs", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    // Select Pool 9
    fireEvent.click(screen.getAllByText("T8B1")[0]);

    // Detail tabs must be visible
    expect(screen.getByRole("button", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Compatible Pumps/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Inventory" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Installation History" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Drawings / Documents" })).toBeTruthy();
  });

  it("switching detail tabs shows Inventory, Compatible Pumps, and Drawings correctly", async () => {
    render(<Seal />);
    await screen.findAllByText("T8B1");

    // Select Pool 9
    fireEvent.click(screen.getAllByText("T8B1")[0]);

    // Switch to Inventory tab
    fireEvent.click(screen.getByRole("button", { name: "Inventory" }));
    expect(screen.getByText("Complete Seal Stock & Configuration")).toBeTruthy();
    expect(screen.getByText("Storage Location")).toBeTruthy();
    expect(screen.getByText("TAP DMI")).toBeTruthy();

    // Switch to Compatible Pumps tab
    fireEvent.click(screen.getByRole("button", { name: /Compatible Pumps/i }));
    expect(screen.getByText("210-P-1A")).toBeTruthy();
    expect(screen.getByText("210-P-1B")).toBeTruthy();
    expect(screen.getAllByText("Open Pump →").length).toBe(2);
    expect(screen.getAllByText("Asset 360 →").length).toBe(2);

    // Switch to Drawings tab
    fireEvent.click(screen.getByRole("button", { name: "Drawings / Documents" }));
    expect(screen.getByText("Drawings & Technical Documents")).toBeTruthy();
    expect(screen.getByText("E12893")).toBeTruthy();
    expect(screen.getByText("E13062")).toBeTruthy();
  });

  it("compatible pump button in detail view triggers navigation callback", async () => {
    const onNavigate = vi.fn();
    render(<Seal onNavigate={onNavigate} />);
    await screen.findAllByText("T8B1");

    // Select Pool 9
    fireEvent.click(screen.getAllByText("T8B1")[0]);

    // Switch to Compatible Pumps tab
    fireEvent.click(screen.getByRole("button", { name: /Compatible Pumps/i }));

    // Click Open Pump
    fireEvent.click(screen.getAllByText("Open Pump →")[0]);
    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "210-P-1A" });

    // Click Asset 360
    fireEvent.click(screen.getAllByText("Asset 360 →")[0]);
    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "210-P-1A" });
  });

  it("Registered Seals KPI reflects authoritative seal registry count (3) NOT stock pools count (2), and registry seal without stock remains represented", async () => {
    const REGISTRY_FIXTURE = [
      { seal_code: "REG-001", seal_name: "John Crane Type 21", manufacturer: "John Crane", status: "ACTIVE" },
      { seal_code: "REG-002", seal_name: "Flowserve ISC2", manufacturer: "Flowserve", status: "ACTIVE" },
      { seal_code: "REG-003", seal_name: "Chesterton 155", manufacturer: "Chesterton", status: "STANDBY" },
    ];
    const STOCK_POOLS_FIXTURE = [
      {
        stock_pool_id: 1,
        seal_type: "T48MP",
        nominal_size: '1-7/8"',
        quantity_on_hand: 2,
        quantity_available: 2,
        verification_status: "CONFIRMED",
        applications: [{ equipment_tag: "945-P-1A" }],
      },
      {
        stock_pool_id: 2,
        seal_type: "T8B1",
        nominal_size: '2-3/4"',
        quantity_on_hand: 4,
        quantity_available: 4,
        verification_status: "CONFIRMED",
        applications: [{ equipment_tag: "210-P-1A" }],
      },
    ];

    getSeals.mockResolvedValue(REGISTRY_FIXTURE);
    getMechanicalSealStock.mockResolvedValue({
      items: STOCK_POOLS_FIXTURE,
      total: 2,
      total_quantity: 6,
      limit: 100,
      offset: 0,
    });

    render(<Seal />);
    await screen.findByText("T48MP");

    // 1. Registered Seals KPI MUST be 3 (authoritative registry count), NOT 2 (stock pools count) and NOT 5 (conflated total rows)
    const registeredCardValue = screen.getByText("Registered Seals").nextElementSibling?.textContent;
    expect(registeredCardValue).toBe("3");
    expect(registeredCardValue).not.toBe("2");
    expect(registeredCardValue).not.toBe("5");

    // 2. Complete Seal Stock KPI MUST be Stock V1 inventory (6 sets)
    expect(screen.getByText("6 sets")).toBeTruthy();

    // 3. Registry seals without stock remain represented and DO NOT disappear from unified workspace
    expect(screen.getByText("REG-001")).toBeTruthy();
    expect(screen.getByText("REG-002")).toBeTruthy();
    expect(screen.getByText("REG-003")).toBeTruthy();

    // Unmanaged registry seals display Available Stock = "N/A"
    const naBadges = screen.getAllByText("N/A");
    expect(naBadges.length).toBeGreaterThanOrEqual(3);
  });
});

describe("LTSA Mechanical Seal Unified Workspace - Navigation & Routing", () => {
  it("LTSAWorkspace sidebar does NOT contain 'Mechanical Seal Stock' tab", () => {
    render(<LTSAWorkspace initialActiveKey="seal" />);
    // "Mechanical Seal" tab must be present
    expect(screen.getByRole("tab", { name: "Mechanical Seal" })).toBeTruthy();
    // "Mechanical Seal Stock" tab must NOT be in the tabs list
    expect(screen.queryByRole("tab", { name: "Mechanical Seal Stock" })).toBeNull();
  });

  it("parseWorkspaceLocation maps legacy /ltsa/inventory to seal workspace", () => {
    const location = parseWorkspaceLocation("/ltsa/inventory");
    expect(location).toEqual({ key: "seal", context: {} });
  });
});
