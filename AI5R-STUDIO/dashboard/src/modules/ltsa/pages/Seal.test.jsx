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
});

afterEach(() => {
  vi.clearAllMocks();
});

const RAW_SEALS = [
  { seal_code: "SC-101", seal_name: "Flowserve ISC2", manufacturer: "Flowserve", status: "ACTIVE" },
  { seal_code: "SC-102", seal_name: "AESSEAL P8", manufacturer: "AESSEAL", status: "FAULT" },
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
    expect(screen.queryByText("SC-101")).toBeNull();
  });

  it("shows the existing empty state when the API returns zero seals -- no fabricated data", async () => {
    getSeals.mockResolvedValue([]);
    render(<Seal />);

    expect(await screen.findByText(/no seals available/i)).toBeTruthy();
  });

  it("renders every seal returned by the real API, mapped to the registry table's shape", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);

    expect(await screen.findByText("SC-101")).toBeTruthy();
    expect(screen.getByText("SC-102")).toBeTruthy();
    expect(getSeals).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the detail panel before any seal is selected", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);
    await screen.findByText("SC-101");

    expect(screen.getByText(/no seal selected/i)).toBeTruthy();
  });

  it("shows the selected seal's detail, mapped from the real API record, when a row is clicked", async () => {
    getSeals.mockResolvedValue(RAW_SEALS);
    render(<Seal />);
    await screen.findByText("SC-101");

    fireEvent.click(screen.getByText("SC-101"));

    expect(screen.getByRole("heading", { name: "Flowserve ISC2" })).toBeTruthy();
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
      expect(screen.getByText(seal.code)).toBeTruthy();
    });
  });

  it("shows the selected seal's detail when a registry row is clicked", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.click(screen.getByText("SC-003"));

    expect(screen.getByRole("heading", { name: "Flowserve ISC2" })).toBeTruthy();
  });

  it("filters the registry table by search text", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "AESSEAL" } });

    expect(screen.getByText("SC-005")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("SC-007")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
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
    await screen.findByText("SC-101");

    fireEvent.click(screen.getByText("SC-101"));

    // "211-P-1A" now legitimately appears twice (ChromeBar breadcrumb link
    // and the Compatibility section's "Related Pumps" RefGroup entry) --
    // findAllByText, not findByText, since both are correct per the Open
    // Design's own component hierarchy.
    expect((await screen.findAllByText("211-P-1A")).length).toBeGreaterThan(0);
  });

  it("never overwrites sealsProp's own compatiblePumps with an empty compatibilityRecords default", () => {
    // getSealCompatibility is never called on the sealsProp path (asserted
    // elsewhere), so this proves sealsProp's own "PMP-001" fixture value
    // survives untouched -- the bug this test guards against would show
    // compatiblePumps silently reset to [].
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

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
  it("calls onNavigate('pump', {selectId}) when the breadcrumb pump link is clicked", () => {
    const onNavigate = vi.fn();
    render(<Seal seals={sampleSeals} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText("SC-001"));

    fireEvent.click(screen.getByRole("button", { name: "211-P-1A" }));

    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "211-P-1A" });
  });

  it("calls onNavigate('pump', {selectId}) when the Action Bar's 'Buka Pump' is clicked", () => {
    const onNavigate = vi.fn();
    render(<Seal seals={sampleSeals} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText("SC-001"));

    fireEvent.click(screen.getByText("Buka Pump →"));

    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "211-P-1A" });
  });

  it("calls onNavigate('drawing', {assetTag}) when 'Buka Drawing' is clicked -- MWO-LTSA-051A: passes the resolved pump tag so Drawing Workspace can fetch that pump's real drawings", () => {
    const onNavigate = vi.fn();
    render(<Seal seals={sampleSeals} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText("SC-001"));

    fireEvent.click(screen.getByText("Buka Drawing →"));

    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: "211-P-1A" });
  });

  it("shows no pump link (breadcrumb or Action Bar) when the seal has no compatible pump", () => {
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} onNavigate={vi.fn()} />);

    fireEvent.click(screen.getByText(seal.code));

    // MWO-LTSA-048 -- "Pompa Tidak Diketahui" ("Pump Unknown") replaced
    // with "Outside LTSA" (definite fact, not missing/uncertain data).
    expect(screen.getByText("Outside LTSA")).toBeTruthy();
    expect(screen.queryByText("Buka Pump →")).toBeNull();
  });

  it("does not throw when 'Buka Drawing' is clicked with no onNavigate prop supplied", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(() => fireEvent.click(screen.getByText("Buka Drawing →"))).not.toThrow();
  });
});

// MWO-LTSA-044 P0 -- Contract Coverage card, derived from the same
// resolvedAssetCode signal already driving the breadcrumb/Action Bar pump
// link and Engineering AI availability (no dedicated backend field exists
// yet -- see SealOpenDesignView.jsx's own coverageMeta comment).
describe("Seal workspace -- Contract Coverage card (MWO-LTSA-044)", () => {
  it("shows 'LTSA Covered' for a seal that resolves a compatible pump", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    // "LTSA Covered" legitimately appears twice: the Contract Coverage
    // card and the Action Bar's denser .meta line -- both reuse the same
    // coverageMeta.label, per this MWO's own P2 Action Bar requirement.
    expect(screen.getAllByText("LTSA Covered").length).toBeGreaterThan(0);
  });

  it("shows 'Outside LTSA Contract' with the explanatory note and Unavailable list for a seal with no compatible pump", () => {
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText(seal.code));

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
