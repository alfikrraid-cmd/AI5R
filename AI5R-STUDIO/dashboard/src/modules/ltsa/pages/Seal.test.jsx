import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Seal from "./Seal";
import {
  getSeals,
  getSealCompatibility,
  getSealStock,
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
  getDocuments,
  getEngineeringDrawingsForSeal,
  getEngineeringDrawingRevisions,
  getEngineeringDrawingBom,
  getConditionMonitoringReadings,
} from "../../../api/ai5rClient";
import sampleSeals from "../data/sampleSeals";

// MWO-LTSA-041 -- Seal.jsx now fetches real data via getSeals() when no
// `seals` prop is supplied, mirroring Pump.jsx's loading/error/list
// pattern exactly. The `seals` prop still exists, unmodified, as an
// explicit override: when a caller passes it directly (as this file's
// second describe block and the entire Seal.engineeringAI.test.jsx suite
// already do), the fetch is never triggered -- confirmed by those files
// never mocking getSeals at all, only postEngineeringAI where relevant.
// This preserves every existing test in both files unchanged.
//
// MWO-LTSA-042 -- getSealCompatibility/getSealStock added to this mock
// (Seal.jsx now imports and calls both alongside getSeals()). Additive
// only: no existing test's assertions changed, this just keeps the
// mocked module's exports in sync with what Seal.jsx actually imports,
// so the real-fetch-path tests below don't throw
// "getSealCompatibility is not a function".
//
// MWO-LTSA-042A -- getPMSchedules/getCMReports/getWorkOrders added, same
// reason: Seal.jsx now fetches these (Related Engineering groups in
// SealOpenDesignView), so any test that selects a seal with a resolvable
// asset code triggers these calls. Additive only.

vi.mock("../../../api/ai5rClient", () => ({
  getSeals: vi.fn(),
  getSealCompatibility: vi.fn(),
  getSealStock: vi.fn(),
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
  getDocuments: vi.fn(),
  getEngineeringDrawingsForSeal: vi.fn(),
  getEngineeringDrawingRevisions: vi.fn(),
  getEngineeringDrawingBom: vi.fn(),
  getConditionMonitoringReadings: vi.fn(),
}));

beforeEach(() => {
  // Safe default so any seal selection's Engineering AI request (existing,
  // unrelated behavior this MWO doesn't touch -- see
  // Seal.engineeringAI.test.jsx for its own dedicated coverage) resolves
  // instead of throwing on an unmocked call.
  postEngineeringAI.mockResolvedValue({
    summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
    risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
    token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
  });
  // Safe defaults -- individual tests below override with mockResolvedValue
  // where the compatibility/stock content itself matters.
  getSealCompatibility.mockResolvedValue([]);
  getSealStock.mockResolvedValue([]);
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
  // R2A -- getDocuments() added, same reason as getSealCompatibility/
  // getSealStock above: Seal.jsx now fetches it (Documents tab real read
  // path, SealOpenDesignView.jsx), so any real-fetch-path test triggers
  // this call. Additive only, keeps the mock in sync.
  getDocuments.mockResolvedValue([]);
  // R2B -- getEngineeringDrawingsForSeal/Revisions/Bom added, same
  // reason: Seal.jsx now fetches these once a seal is selected (Drawings/
  // BOM tabs, SealOpenDesignView.jsx). Additive only.
  getEngineeringDrawingsForSeal.mockResolvedValue([]);
  getEngineeringDrawingRevisions.mockResolvedValue([]);
  getEngineeringDrawingBom.mockResolvedValue([]);
  // MWO-R2C3 -- getConditionMonitoringReadings added, same reason: Seal.jsx
  // now fetches it (genuine Condition Monitoring, bounded to the resolved
  // asset). Additive only.
  getConditionMonitoringReadings.mockResolvedValue([]);
});

afterEach(() => {
  vi.clearAllMocks();
});

// MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- seal_id added (raw API
// shape). Synthetic test data; not derived from a real migration 044
// run (which only maps 'John Crane' manufacturers today).
const RAW_SEALS = [
  { seal_code: "SC-101", seal_id: "MS-FS-0101", seal_name: "Flowserve ISC2", manufacturer: "Flowserve", status: "ACTIVE" },
  { seal_code: "SC-102", seal_id: "MS-AS-0102", seal_name: "AESSEAL P8", manufacturer: "AESSEAL", status: "FAULT" },
];

describe("Seal workspace page -- real backend fetch (MWO-LTSA-041)", () => {
  it("renders the page header immediately, before the fetch resolves", () => {
    getSeals.mockReturnValue(new Promise(() => {}));
    render(<Seal />);

    expect(screen.getByRole("heading", { name: "Seal Workspace" })).toBeTruthy();
  });

  it("renders a loading state before the API resolves", () => {
    getSeals.mockReturnValue(new Promise(() => {}));
    render(<Seal />);

    expect(screen.getByText(/loading seals/i)).toBeTruthy();
  });

  it("renders list API errors without fallback mock data", async () => {
    getSeals.mockRejectedValue(new Error("API unavailable"));
    render(<Seal />);

    expect(await screen.findByText("Seals could not be loaded.")).toBeTruthy();
    expect(screen.queryByText("MS-FS-0101")).toBeNull();
  });

  it("shows the existing empty state when the API returns zero seals -- no fabricated data", async () => {
    getSeals.mockResolvedValue([]);
    render(<Seal />);

    expect(await screen.findByText(/no seals available/i)).toBeTruthy();
  });

  it("renders every seal returned by the real API, mapped to the registry table's shape", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);

    expect(await screen.findByText("MS-FS-0101")).toBeTruthy();
    expect(screen.getByText("MS-AS-0102")).toBeTruthy();
    expect(getSeals).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the detail panel before any seal is selected", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);
    await screen.findByText("MS-FS-0101");

    expect(screen.getByText(/no seal selected/i)).toBeTruthy();
  });

  it("shows the selected seal's detail, mapped from the real API record, when a row is clicked", async () => {
    // UI-D1.2 -- the identity header's <h1> is the seal's CODE; name is
    // adjacent subtitle text, not a second heading. Row selection now
    // happens via the registry's Seal ID column (MS-FS-0101), not the
    // legacy code (SealOpenDesignView's own heading is unchanged -- it
    // still renders seal.code).
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);
    await screen.findByText("MS-FS-0101");

    fireEvent.click(screen.getByText("MS-FS-0101"));

    expect(screen.getByRole("heading", { name: "SC-101" })).toBeTruthy();
    expect(screen.getAllByText("Flowserve ISC2").length).toBeGreaterThan(0);
  });

  it("never calls getSeals when a seals prop is explicitly provided (override, not the default path)", () => {
    render(<Seal seals={sampleSeals} />);

    expect(getSeals).not.toHaveBeenCalled();
  });
});

describe("Seal workspace page -- with injected data (fixture, not shown to real users)", () => {
  it("renders every seal in the registry table when data is provided", () => {
    render(<Seal seals={sampleSeals} />);

    sampleSeals.forEach((seal) => {
      expect(screen.getByText(seal.sealId)).toBeTruthy();
    });
  });

  it("shows the selected seal's detail when a registry row is clicked", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.click(screen.getByText("MS-FS-0003"));

    expect(screen.getByRole("heading", { name: "SC-003" })).toBeTruthy();
    expect(screen.getAllByText("Flowserve ISC2").length).toBeGreaterThan(0);
  });

  it("filters the registry table by search text", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "AESSEAL" } });

    expect(screen.getByText("MS-AS-0005")).toBeTruthy();
    expect(screen.queryByText("MS-JC-0001")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("MS-JC-0007")).toBeTruthy();
    expect(screen.queryByText("MS-JC-0001")).toBeNull();
  });
});

// MWO-LTSA-042 -- Compatible Pumps resolution (real backend path), Open
// Pump/Open Drawing/PM History/CM History navigation. Reuses this file's
// existing RAW_SEALS/beforeEach setup exactly.
describe("Seal workspace -- Compatible Pumps resolved from getSealCompatibility (MWO-LTSA-042)", () => {
  it("merges compatiblePumps from the real seal-compatibility endpoint for the fetched path", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    getSealCompatibility.mockResolvedValue([
      { seal_code: "SC-101", pump_tag_number: "211-P-1A", notes: null },
    ]);
    render(<Seal onNavigate={vi.fn()} />);
    await screen.findByText("MS-FS-0101");

    fireEvent.click(screen.getByText("MS-FS-0101"));
    // UI-D1.2 -- Compatible Pumps now render inside the Compatible tab's
    // "Related Pumps" RefGroup, not always-visible.
    fireEvent.click(screen.getByRole("tab", { name: "Compatible" }));

    expect((await screen.findAllByText("211-P-1A")).length).toBeGreaterThan(0);
  });

  it("never overwrites sealsProp's own compatiblePumps with an empty compatibilityRecords default", () => {
    // getSealCompatibility is never called on the sealsProp path (asserted
    // elsewhere), so this proves sealsProp's own "PMP-001" fixture value
    // survives untouched -- the bug this test guards against would show
    // compatiblePumps silently reset to [].
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));
    fireEvent.click(screen.getByRole("tab", { name: "Compatible" }));

    expect(screen.getByText("PMP-001")).toBeTruthy();
  });
});

// MWO-LTSA-042A -- SealOpenDesignView replaces the old Compatible Pumps
// badges / standalone "PM History"/"CM History" Quick Actions buttons
// (removed, no equivalent in the approved Open Design's component
// hierarchy) with a non-interactive Compatibility "Related Pumps" RefGroup
// plus the ChromeBar breadcrumb link and the sticky Action Bar's "Buka
// Pump →" / "Buka Drawing →" buttons, both wired to the same
// onOpenPump/onOpenDrawing -> onNavigate(key, context) mechanism as
// before. Related PM/CM/Work Order data now renders inline via the
// Related Engineering RefGroup sections (covered by the dedicated
// describe block below), not via a click-to-navigate button.
describe("Seal workspace -- Open Pump / Open Drawing navigation (MWO-LTSA-042A)", () => {
  // UI-D1.2 -- deleted: "calls onNavigate('pump', {selectId}) when the
  // breadcrumb pump link is clicked". This asserted the old ChromeBar
  // breadcrumb's clickable pump-tag button (bare tag text as a <button>,
  // separate from the Action Bar's "Buka Pump ->"). The Compatible tab's
  // "Related Pumps" RefGroup items carry no onClick (compatibilityGroups
  // in SealOpenDesignView.jsx), so they render as plain <span>, and no
  // other element renders a bare resolved-pump-tag button anywhere in the
  // current file -- confirmed by reading the full component source. Per
  // this mission's "do not restore obsolete DOM wrappers" / "do not modify
  // production behavior merely to satisfy an obsolete test" rules, no
  // breadcrumb button was reintroduced just to keep this test green; the
  // same onNavigate("pump", {selectId}) behavior remains fully covered by
  // the Action Bar's "Buka Pump ->" test directly below.

  // UI-D1.2 -- known PRE_EXISTING_UNRELATED failure, not touched: the
  // "Buka Pump ->" button (unconditional, not tab-gated) still calls
  // onNavigate("pump", {selectId: resolvedAssetCode}) exactly as before.
  // This test's own expected value ("211-P-1A") does not match
  // sampleSeals.js's real SC-001.compatiblePumps (["PMP-001","PMP-002"]),
  // so resolvedAssetCode actually resolves to "PMP-001" -- a fixture/test
  // drift that predates this phase (sampleSeals.js, Seal.test.jsx, and
  // resolveAssetCode() are byte-identical to HEAD; confirmed via
  // `git diff HEAD` before this migration touched anything). Left failing
  // and reported, per this mission's own section 8 instruction not to
  // silently absorb known pre-existing fixture drift.
  it("calls onNavigate('pump', {selectId}) when the Action Bar's 'Buka Pump' is clicked", () => {
    const onNavigate = vi.fn();
    render(<Seal seals={sampleSeals} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));

    fireEvent.click(screen.getByText("Buka Pump →"));

    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "211-P-1A" });
  });

  // UI-D1.2 -- "Buka Drawing ->" now lives under the Documents tab (fixed
  // below). Once reachable, this test hits the SAME PRE_EXISTING_UNRELATED
  // fixture drift as "Buka Pump" above (assetTag also derives from
  // resolvedAssetCode = seal.compatiblePumps[0] = "PMP-001", not the
  // test's expected "211-P-1A") -- left failing and reported, not touched.
  it("calls onNavigate('drawing', {assetTag}) when 'Buka Drawing' is clicked -- MWO-LTSA-051A: passes the resolved pump tag so Drawing Workspace can fetch that pump's real drawings", () => {
    const onNavigate = vi.fn();
    render(<Seal seals={sampleSeals} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    fireEvent.click(screen.getByText("Buka Drawing →"));

    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: "211-P-1A" });
  });

  it("shows no pump link (Action Bar) when the seal has no compatible pump", () => {
    // UI-D1.2 -- the old standalone `<span>Outside LTSA</span>` badge was
    // folded into the identity header's subtitle text ("Outside LTSA
    // scope", AssetIdentityHeader.jsx), a wording refinement made as part
    // of this phase's redesign, not a lost fact -- same real
    // !resolvedAssetCode signal, still an unambiguous positive statement.
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} onNavigate={vi.fn()} />);

    fireEvent.click(screen.getByText(seal.sealId));

    expect(screen.getByText(/Outside LTSA scope/)).toBeTruthy();
    expect(screen.queryByText("Buka Pump →")).toBeNull();
  });

  it("does not throw when 'Buka Drawing' is clicked with no onNavigate prop supplied", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    expect(() => fireEvent.click(screen.getByText("Buka Drawing →"))).not.toThrow();
  });
});

describe("Seal workspace -- bounded genuine Condition Monitoring fetch (MWO-R2C3)", () => {
  it("calls getConditionMonitoringReadings with the resolved asset code only -- never the fleet-wide fetch", async () => {
    render(<Seal seals={sampleSeals} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));

    await screen.findByText("MS-JC-0001");

    expect(getConditionMonitoringReadings).toHaveBeenCalledWith({ assetCode: "PMP-001" });
    expect(getConditionMonitoringReadings).toHaveBeenCalledTimes(1);
  });

  it("keeps getCMReports (legacy Corrective Maintenance) as a separate call, not the source of genuine readings", async () => {
    render(<Seal seals={sampleSeals} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));

    await screen.findByText("MS-JC-0001");

    // Both fire (each feeds its own, separate display group), but with
    // no shared arguments/return value coupling them -- proving Related
    // Condition Monitoring's data does not come from getCMReports().
    expect(getCMReports).toHaveBeenCalled();
    expect(getConditionMonitoringReadings).toHaveBeenCalledWith({ assetCode: "PMP-001" });
  });
});

// MWO-LTSA-044 P0 -- Contract Coverage card, derived from the same
// resolvedAssetCode signal already driving the breadcrumb/Action Bar pump
// link and Engineering AI availability (no dedicated backend field exists
// yet -- see SealOpenDesignView.jsx's own coverageMeta comment).
describe("Seal workspace -- Contract Coverage card (MWO-LTSA-044)", () => {
  it("shows 'LTSA Covered' for a seal that resolves a compatible pump", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));

    // "LTSA Covered" legitimately appears twice: the Contract Coverage
    // card and the Action Bar's denser .meta line -- both reuse the same
    // coverageMeta.label, per this MWO's own P2 Action Bar requirement.
    expect(screen.getAllByText("LTSA Covered").length).toBeGreaterThan(0);
  });

  it("shows 'Outside LTSA Contract' with the explanatory note and Unavailable list for a seal with no compatible pump", () => {
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText(seal.sealId));

    expect(screen.getAllByText("Outside LTSA Contract").length).toBeGreaterThan(0);
    // MWO-LTSA-047 -- message shortened further to one short sentence.
    expect(screen.getByText(/outside active LTSA scope/i)).toBeTruthy();
    expect(screen.getByText("PM History")).toBeTruthy();
    // "Engineering AI" also matches the section eyebrow further down the
    // page -- getAllByText, not getByText.
    expect(screen.getAllByText("Engineering AI").length).toBeGreaterThan(0);
    expect(screen.getByText("Asset Analytics")).toBeTruthy();
  });
});
