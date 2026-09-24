import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Pump from "./Pump";
import {
  getPumps, getPump, getPumpOpenWorkOrders, getPumpLifecycle, getSeals, getSealCompatibility, postEngineeringAI,
} from "../../../api/ai5rClient";

// postEngineeringAI stubbed here only because Pump.jsx now calls it (MWO:
// Pump Workspace Engineering AI integration) -- no existing assertion in
// this file was changed to accommodate that; every test below verifies
// exactly what it verified before.
//
// MWO-LTSA-065 -- getPumpLastPM/getPumpSpareParts/getPMSchedules/
// getCMReports/getWorkOrders are gone: Pump.jsx now fetches ONE endpoint,
// getPumpLifecycle(tag), for everything Related Engineering/Current
// State/Compatibility used to resolve from five separate calls.
//
// MWO-PUMP-REGISTRY-N1-REMOVAL-R1 -- getPumpOpenWorkOrders is mocked here
// only so withResolvedOpenWO()/getPumpOpenWorkOrders() staying importable
// elsewhere doesn't break this file's module mock shape. The Pump
// registry's initial load no longer calls it at all (it used to fire one
// call per pump -- 252 in production -- via Promise.all, colliding with
// nginx's own rate limiter for no real data, since the Work Order n8n
// LIST workflow isn't deployed and work_order has 0 production rows
// regardless). See the "N+1 removed" describe block below for the actual
// proof.
// MWO-LTSA-UI-V2-001 -- Seal & Inventory: getSeals()/getSealCompatibility()
// are the two already-existing endpoints Seal.jsx already fetches, now
// also fetched once (not per-pump) by Pump.jsx to enrich lifecycle's
// inventory array with real Type/Size + the full compatible-pump list. No
// new backend route -- see sealMapping.js's buildSealInventoryGroups().
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  getPump: vi.fn(),
  getPumpOpenWorkOrders: vi.fn(),
  getPumpLifecycle: vi.fn(),
  getSeals: vi.fn(),
  getSealCompatibility: vi.fn(),
  postEngineeringAI: vi.fn(),
}));

const PUMPS = [
  {
    tag_number: "211-P-1A",
    name: "Boiler Feedwater Pump 1A",
    area: "Boiler House",
    manufacturer: "Sulzer",
    pump_type: "Centrifugal (API 610)",
    seal_type: "John Crane Type 21",
    location: "Unit 2 - Boiler House",
    status: "RUNNING",
    criticality: "HIGH",
  },
  {
    tag_number: "305-P-2",
    name: "Cooling Water Circulation Pump",
    area: "Utilities",
    manufacturer: "Flowserve",
    pump_type: "Vertical Turbine",
    seal_type: "Flowserve ISC2",
    location: "Utilities - Cooling Tower Basin",
    status: "RUNNING",
    criticality: "MEDIUM",
  },
  {
    tag_number: "418-P-1",
    name: "Amine Circulation Pump",
    area: "Gas Treating",
    manufacturer: "KSB",
    pump_type: "Centrifugal (ANSI)",
    seal_type: "AESSEAL P8",
    location: "Gas Treating Unit",
    status: "RUNNING",
    criticality: "MEDIUM",
  },
  {
    tag_number: "641-P-5",
    name: "Sour Water Stripper Bottoms Pump",
    area: "SWS Unit",
    manufacturer: "ITT Goulds",
    pump_type: "Centrifugal (API 610 OH2)",
    seal_type: "John Crane 502",
    location: "SWS Unit",
    status: "FAULT",
    criticality: "HIGH",
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

const EMPTY_LIFECYCLE_DATA = {
  tag_number: null,
  pump: null,
  current_state: {
    current_installation: null,
    current_seal: null,
    elapsed_service_days: null,
    running_hours_derived: null,
    last_pm: null,
    next_pm: null,
    last_cm: null,
    last_failure: null,
    open_work_orders: [],
  },
  timeline: [],
  analytics: {
    elapsed_service_days: null,
    pm_count: 0,
    cm_count: 0,
    failure_count: 0,
    mtbf: null,
    mtbr: null,
    average_seal_life: null,
    health_index: null,
    availability: null,
    reliability: null,
  },
  related_engineering: {
    pm_schedules: [],
    cm_reports: [],
    work_orders: [],
    breakdown_history: [],
    drawings: [],
    documents: [],
    inventory: [],
  },
};

function loadPumps(records = PUMPS) {
  getPumps.mockResolvedValue(records);
  // Not called by the initial registry load any more (see the "N+1
  // removed" describe block below) -- mocked only so an unexpected call
  // from unrelated code would fail loudly instead of hanging.
  getPumpOpenWorkOrders.mockResolvedValue({ success: true, openWO: 0, data: [] });
  getPumpLifecycle.mockResolvedValue({ success: true, tag_number: null, data: EMPTY_LIFECYCLE_DATA });
  getSeals.mockResolvedValue([]);
  getSealCompatibility.mockResolvedValue([]);
  postEngineeringAI.mockResolvedValue({
    summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
    risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
    token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
  });
}

describe("Pump workspace page", () => {
  it("renders the page header", async () => {
    loadPumps();
    render(<Pump />);

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    await screen.findByText("211-P-1A");
  });

  it("renders a loading state before the API resolves", () => {
    getPumps.mockReturnValue(new Promise(() => {}));
    render(<Pump />);

    expect(screen.getByText("Loading pumps...")).toBeTruthy();
  });

  it("renders a tagged Asset 360 pump from the core endpoint before the registry resolves", async () => {
    getPumps.mockReturnValue(new Promise(() => {}));
    getPump.mockResolvedValue(PUMPS[0]);
    getPumpLifecycle.mockReturnValue(new Promise(() => {}));
    getSeals.mockResolvedValue([]);
    getSealCompatibility.mockResolvedValue([]);
    postEngineeringAI.mockResolvedValue({ summary: "", findings: [], confidence: null, evidence: [], recommendations: [], risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0, token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null });

    render(<Pump navContext={{ selectId: PUMPS[0].tag_number }} />);

    expect((await screen.findAllByText(PUMPS[0].tag_number)).length).toBeGreaterThan(0);
    expect(screen.queryByText("Loading pumps...")).toBeNull();
    expect(getPump).toHaveBeenCalledWith(PUMPS[0].tag_number);
  });

  it("keeps the core pump visible when secondary lifecycle loading fails", async () => {
    getPumps.mockReturnValue(new Promise(() => {}));
    getPump.mockResolvedValue(PUMPS[0]);
    getPumpLifecycle.mockRejectedValue(new Error("secondary unavailable"));
    getSeals.mockResolvedValue([]);
    getSealCompatibility.mockResolvedValue([]);
    postEngineeringAI.mockResolvedValue({ summary: "", findings: [], confidence: null, evidence: [], recommendations: [], risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0, token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null });

    render(<Pump navContext={{ selectId: PUMPS[0].tag_number }} />);

    expect((await screen.findAllByText(PUMPS[0].tag_number)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(PUMPS[0].name).length).toBeGreaterThan(0);
  });

  it("renders list API errors without fallback mock data", async () => {
    getPumps.mockRejectedValue(new Error("API unavailable"));
    render(<Pump />);

    expect(await screen.findByText("Pumps could not be loaded.")).toBeTruthy();
    expect(screen.queryByText("211-P-1A")).toBeNull();
  });

  it("renders every pump from the canonical API in the registry table", async () => {
    loadPumps();
    render(<Pump />);

    for (const pump of PUMPS) {
      expect(await screen.findByText(pump.tag_number)).toBeTruthy();
    }
    expect(getPumps).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the detail panel before any pump is selected", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("211-P-1A");

    expect(screen.getByText(/no pump selected/i)).toBeTruthy();
  });

  it("shows the selected pump's detail when a registry row is clicked", async () => {
    // UI-D1.2 -- the Open Design identity header's <h1> is the pump's
    // TAG (the canonical asset code); name/service is real, adjacent
    // subtitle text, not a second heading. Same semantics as before
    // (tag + name both render), different element type.
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));

    expect(await screen.findByRole("heading", { name: "305-P-2" })).toBeTruthy();
    // Name also still appears in the registry row, hence getAllByText.
    expect(screen.getAllByText(/Cooling Water Circulation Pump/).length).toBeGreaterThan(0);
  });

  it("filters the registry table by search text", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("211-P-1A");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Amine" } });

    expect(screen.getByText("418-P-1")).toBeTruthy();
    expect(screen.queryByText("211-P-1A")).toBeNull();
  });

  it("filters the registry table by status", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("211-P-1A");

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.queryByText("211-P-1A")).toBeNull();
  });

  it("shows an empty state in the registry when no pump matches the search", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("211-P-1A");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-pump-xyz" } });

    expect(screen.getByText(/no pumps match/i)).toBeTruthy();
  });

  it("opens the Create PM Schedule dialog from the selected pump's Quick Actions", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    fireEvent.click(await screen.findByRole("button", { name: "Create PM" }));

    expect(screen.getByRole("heading", { name: "Create PM Schedule" })).toBeTruthy();
  });

  it("opens the Create CM Report dialog from the selected pump's Quick Actions", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    fireEvent.click(await screen.findByRole("button", { name: "Create CM" }));

    expect(screen.getByRole("heading", { name: "Create CM Report" })).toBeTruthy();
  });

  it("navigates to Asset 360 already scoped to this pump when Open Asset 360 is clicked from the Asset360 tab", async () => {
    // UI-D1.2 -- the sticky Action Bar's "View History ->" button is gone;
    // the same onViewHistory callback now lives on the Asset360 tab's own
    // "Open Asset 360 ->" button.
    loadPumps();
    const onNavigate = vi.fn();
    render(<Pump onNavigate={onNavigate} />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "305-P-2" });
    fireEvent.click(screen.getByRole("tab", { name: "Asset360" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open Asset 360 →" }));

    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "305-P-2" });
  });

  // MWO-PUMP-REGISTRY-N1-REMOVAL-R1 -- replaces the old "resolves openWO
  // per pump via the canonical API" test, which asserted exactly the N+1
  // fan-out this MWO removes (one getPumpOpenWorkOrders call per pump,
  // fired unconditionally on every registry load).
  describe("Pump registry N+1 removed (MWO-PUMP-REGISTRY-N1-REMOVAL-R1)", () => {
    it("calls getPumps exactly once on initial load", async () => {
      loadPumps();
      render(<Pump />);
      await screen.findByText("211-P-1A");

      expect(getPumps).toHaveBeenCalledOnce();
    });

    it("makes ZERO getPumpOpenWorkOrders calls on initial load", async () => {
      loadPumps();
      render(<Pump />);
      await screen.findByText("211-P-1A");

      expect(getPumpOpenWorkOrders).not.toHaveBeenCalled();
    });

    it("still makes ZERO per-pump Work Order calls with 252 pumps (production-scale)", async () => {
      const manyPumps = Array.from({ length: 252 }, (_, i) => ({
        tag_number: `TAG-${i}`,
        name: `Pump ${i}`,
        area: "Area",
        manufacturer: "Mfr",
        pump_type: "Centrifugal",
        seal_type: "Type",
        location: "Loc",
        status: "RUNNING",
        criticality: "MEDIUM",
      }));
      loadPumps(manyPumps);
      render(<Pump />);
      await screen.findByText("TAG-0");

      expect(getPumps).toHaveBeenCalledOnce();
      expect(getPumpOpenWorkOrders).not.toHaveBeenCalled();
    });

    it("renders the registry once the pump list resolves, with no Work Order dependency", async () => {
      loadPumps();
      render(<Pump />);

      for (const pump of PUMPS) {
        expect(await screen.findByText(pump.tag_number)).toBeTruthy();
      }
    });

    it("shows N/A, never a fabricated 0, for openWO since it is never resolved during initial load", async () => {
      loadPumps();
      render(<Pump />);
      await screen.findByText("211-P-1A");

      expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
    });
  });

  it("resolves lifecycle lazily for the selected pump only, via the canonical API", async () => {
    loadPumps();
    getPumpLifecycle.mockResolvedValue({
      success: true,
      tag_number: "305-P-2",
      data: {
        ...EMPTY_LIFECYCLE_DATA,
        tag_number: "305-P-2",
        current_state: {
          ...EMPTY_LIFECYCLE_DATA.current_state,
          last_pm: { maintenance_record_code: "MH-101", performed_at: "2026-06-02T00:00:00Z" },
        },
      },
    });
    render(<Pump />);
    await screen.findByText("305-P-2");

    expect(getPumpLifecycle).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "305-P-2" });

    expect(getPumpLifecycle).toHaveBeenCalledWith("305-P-2");
    // UI-D1.2 -- Last PM/Next PM/Last CM/Last Failure now live under the
    // Performance tab's "Current Status" section (Overview no longer
    // shows Current Status directly).
    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    expect(await screen.findByText(/MH-101/)).toBeTruthy();
    expect(screen.getByText(/2026-06-02/)).toBeTruthy();
  });

  it("resolves Seal Stock Available from lifecycle Stock V1 inventory, lazily for the selected pump only", async () => {
    loadPumps();
    getPumpLifecycle.mockResolvedValue({
      success: true,
      tag_number: "305-P-2",
      data: {
        ...EMPTY_LIFECYCLE_DATA,
        tag_number: "305-P-2",
        related_engineering: {
          ...EMPTY_LIFECYCLE_DATA.related_engineering,
          inventory: [
            { stock_pool_id: "MSSP-011", seal_type: "T48MP", application_size: '3-1/2"', quantity_on_hand: 4, quantity_available: 4, verification_status: "CONFIRMED", stock_location: "Warehouse A" },
          ],
        },
      },
    });
    render(<Pump />);
    await screen.findByText("305-P-2");

    expect(getPumpLifecycle).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "305-P-2" });

    expect(getPumpLifecycle).toHaveBeenCalledWith("305-P-2");
    // UI-D1.2 -- Seal Stock Available stays on the default Overview tab.
    expect(await screen.findByText(/T48MP · 3-1\/2"/)).toBeTruthy();
    expect(screen.getByText("Seal Stock Available")).toBeTruthy();
    expect(screen.queryByText("Compatible Seals")).toBeNull();
    expect(screen.getAllByText("4 sets available").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Warehouse A/).length).toBeGreaterThan(0);
  });

  it("renders current state and related engineering together from the one lifecycle fetch, neither clobbering the other", async () => {
    // Regression guard for the old "two independent resolvers merged onto
    // one pump" concern (MWO-LTSA-065 removed both resolvers): this now
    // proves the single lifecycle fetch's current_state and
    // related_engineering both render from the same response.
    loadPumps();
    getPumpLifecycle.mockResolvedValue({
      success: true,
      tag_number: "305-P-2",
      data: {
        ...EMPTY_LIFECYCLE_DATA,
        tag_number: "305-P-2",
        current_state: {
          ...EMPTY_LIFECYCLE_DATA.current_state,
          last_pm: { maintenance_record_code: "MH-101", performed_at: "2026-06-02T00:00:00Z" },
        },
        related_engineering: {
          ...EMPTY_LIFECYCLE_DATA.related_engineering,
          inventory: [
            { stock_pool_id: "MSSP-011", seal_type: "T48MP", application_size: '3-1/2"', quantity_on_hand: 4, quantity_available: 4, verification_status: "CONFIRMED" },
          ],
        },
      },
    });
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "305-P-2" });

    // UI-D1.2 -- current_state (Performance tab) and related_engineering
    // (Overview tab's Seal Stock card) now render on different tabs; both
    // are still proven to come from the one lifecycle fetch.
    expect(screen.getAllByText("4 sets available").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    expect(await screen.findByText(/MH-101/)).toBeTruthy();
  });
});

// MWO-LTSA-070 -- Engineering Navigation: every engineering object in
// Pump Workspace (lifecycle.timeline events, lifecycle.relatedEngineering
// items) is clickable, reusing the existing onNavigate(key, context)
// mechanism -- no new route, no new page.
describe("Engineering Navigation (MWO-LTSA-070)", () => {
  const NAV_LIFECYCLE_DATA = {
    ...EMPTY_LIFECYCLE_DATA,
    tag_number: "305-P-2",
    timeline: [
      {
        id: "INSTALLATION:INSTL-001-2026",
        event_type: "INSTALLATION",
        occurred_at: "2026-01-06",
        title: "Installation INSTL-001-2026",
        description: "001/INSTL/2026",
        severity: "UNKNOWN",
        source: "INSTALLATION_REPORT",
        derived: false,
        payload: {
          installation_code: "INSTL-001-2026",
          report_no: "001/INSTL/2026",
          drawing_no: "GA-230279",
          engineer: "Muh Taufik",
          seal_code: "SEAL-1",
          report_date: "2026-01-06",
        },
      },
      {
        id: "PM:PM-1",
        event_type: "PM",
        occurred_at: "2026-06-29",
        title: "PM Occurrence PM-1",
        description: null,
        severity: "UNKNOWN",
        source: "PM_OCCURRENCE",
        derived: true,
        payload: {
          pm_occurrence_code: "PM-1",
          pm_schedule_code: "PMS-1",
          asset_code: "305-P-2",
          status: "DONE",
          checklist_completion: { "Flushing Line": true, "Quench Line": true },
        },
      },
      {
        id: "INSPECTION:CMONR-1",
        event_type: "INSPECTION",
        occurred_at: "2026-06-29",
        title: "Condition Monitoring CMONR-1",
        description: "Mechseal Bocor dari drain gland durasi 1/2 detik",
        severity: "UNKNOWN",
        source: "CONDITION_MONITORING_READING",
        derived: true,
        // Same date as PM:PM-1 above -- exercises the Same Visit grouping.
        payload: {
          condition_monitoring_reading_code: "CMONR-1",
          condition_monitoring_schedule_code: "UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx",
          asset_code: "305-P-2",
          pump_operating_state: "Running",
          mechanical_seal_leak_de: true,
          mechanical_seal_leak_nde: null,
          finding: "Mechseal Bocor dari drain gland durasi 1/2 detik",
        },
      },
      {
        id: "INSPECTION:CMONR-2",
        event_type: "INSPECTION",
        occurred_at: "2026-05-15",
        title: "Condition Monitoring CMONR-2",
        description: null,
        severity: "UNKNOWN",
        source: "CONDITION_MONITORING_READING",
        derived: true,
        // A different date than any PM event -- must NOT be flagged Same Visit.
        payload: {
          condition_monitoring_reading_code: "CMONR-2",
          condition_monitoring_schedule_code: "UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx",
          asset_code: "305-P-2",
          pump_operating_state: "Standby",
          mechanical_seal_leak_de: false,
          mechanical_seal_leak_nde: false,
          finding: null,
        },
      },
      {
        id: "CM:CM-1",
        event_type: "CM",
        occurred_at: "2026-08-09",
        title: "CM Report CM-1",
        description: "Seal leak",
        severity: "MAJOR",
        source: "CM_REPORT",
        derived: true,
        payload: { cm_report_code: "CM-1", asset_code: "305-P-2" },
      },
      {
        id: "WORK_ORDER:WO-1",
        event_type: "WORK_ORDER",
        occurred_at: "2026-07-16T00:00:00Z",
        title: "Work Order WO-1",
        description: "Inspect coupling",
        severity: "UNKNOWN",
        source: "WORK_ORDER",
        derived: false,
        payload: { work_order_code: "WO-1", asset_code: "305-P-2" },
      },
      {
        id: "FAILURE:MH-1",
        event_type: "FAILURE",
        occurred_at: "2026-07-15",
        title: "Failure MH-1",
        description: "Seal failure confirmed",
        severity: "UNKNOWN",
        source: "MAINTENANCE_HISTORY",
        derived: true,
        payload: { maintenance_record_code: "MH-1", asset_code: "305-P-2" },
      },
      {
        id: "PM:PM-NO-SCHEDULE",
        event_type: "PM",
        occurred_at: "2026-05-01",
        title: "PM Occurrence PM-NO-SCHEDULE",
        description: null,
        severity: "UNKNOWN",
        source: "PM_OCCURRENCE",
        derived: true,
        // Deliberately no pm_schedule_code and no asset_code -- a real
        // shape for historically-imported data (pm_occurrence_code alone
        // must still be enough to navigate; see the dedicated test below).
        payload: { pm_occurrence_code: "PM-NO-SCHEDULE" },
      },
      {
        id: "PM:PM-EMPTY",
        event_type: "PM",
        occurred_at: "2026-04-01",
        title: "PM Occurrence PM-EMPTY",
        description: null,
        severity: "UNKNOWN",
        source: "PM_OCCURRENCE",
        derived: true,
        // Genuinely no identity at all -- no pm_occurrence_code, no
        // pm_schedule_code, no asset_code. This MWO's own "never guess"
        // rule must leave this non-navigating rather than fabricating a
        // link.
        payload: {},
      },
    ],
    related_engineering: {
      ...EMPTY_LIFECYCLE_DATA.related_engineering,
      pm_schedules: [
        { pm_schedule_code: "PMS-1", asset_code: "305-P-2", procedure: "Quarterly seal inspection", next_due: "2026-09-01", status: "ACTIVE" },
      ],
      cm_reports: [
        { cm_report_code: "CM-2", asset_code: "305-P-2", failure_description: "Vibration trending up", status: "OPEN" },
      ],
      work_orders: [
        { work_order_code: "WO-2", asset_code: "305-P-2", title: "Replace bearing", status: "OPEN" },
      ],
      drawings: [
        { drawing_id: "DOC-1", title: "GA Drawing", document_number: "GA-230279", revision: "B", status: "APPROVED" },
      ],
    },
  };

  function loadNav() {
    loadPumps();
    getPumpLifecycle.mockResolvedValue({ success: true, tag_number: "305-P-2", data: NAV_LIFECYCLE_DATA });
  }

  async function renderAndSelect(onNavigate) {
    // UI-D1.2 -- Timeline, Recent Activities and Related Engineering (every
    // assertion in this describe block) now live under the History tab.
    loadNav();
    render(<Pump onNavigate={onNavigate} />);
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "305-P-2" });
    fireEvent.click(screen.getByRole("tab", { name: "History" }));
  }

  it("installation navigation: clicking an INSTALLATION timeline event opens Installation Workspace scoped to that report", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("Installation INSTL-001-2026"));

    expect(onNavigate).toHaveBeenCalledWith("installation", { selectId: "INSTL-001-2026" });
  });

  it("pm navigation: clicking a PM timeline event opens PM Workspace via the occurrence's own pm_occurrence_code, never the shared pm_schedule_code", async () => {
    // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- a Timeline PM event is
    // always a pm_occurrence record; pm_schedule_code (here "PMS-1") is
    // never a unique identity for historically-imported data (it is the
    // shared "UNSCHEDULED::<workbook>" placeholder in production), so it
    // must never be used as the navigation target.
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("PM Occurrence PM-1"));

    expect(onNavigate).toHaveBeenCalledWith("pm", { occurrenceSelectId: "PM-1", assetTag: "305-P-2" });
  });

  it("pm navigation: clicking a Related Engineering PM schedule opens PM Workspace via its own code", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("PMS-1"));

    expect(onNavigate).toHaveBeenCalledWith("pm", { selectId: "PMS-1" });
  });

  it("cm navigation: clicking a CM timeline event opens CM Workspace scoped to that report", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("CM Report CM-1"));

    expect(onNavigate).toHaveBeenCalledWith("cm", { selectId: "CM-1" });
  });

  it("cm navigation: clicking a Related CM Report opens CM Workspace via its own code", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("CM-2"));

    expect(onNavigate).toHaveBeenCalledWith("cm", { selectId: "CM-2" });
  });

  it("work order navigation: clicking a WORK_ORDER timeline event opens Work Order Workspace scoped to that work order", async () => {
    // MWO-LTSA-UI-V2-001 -- "Work Order WO-1" is one of the 3 most recent
    // timeline events, so it now also appears (non-clickable) in Recent
    // Activities -- getAllByText, not getByText. Index [0] is the Timeline
    // section's own clickable item (DOM order: Timeline section precedes
    // Recent Activities section within the History tab body).
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click((await screen.findAllByText("Work Order WO-1"))[0]);

    expect(onNavigate).toHaveBeenCalledWith("workorder", { selectId: "WO-1" });
  });

  it("cmon navigation: clicking an INSPECTION timeline event opens Condition Monitoring's Readings view via the reading's own code", async () => {
    // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- condition_monitoring_reading_code,
    // never condition_monitoring_schedule_code (the shared UNSCHEDULED::*
    // placeholder for historical data, same reasoning as PM above).
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("Condition Monitoring CMONR-1"));

    expect(onNavigate).toHaveBeenCalledWith("cmon", { readingSelectId: "CMONR-1", assetTag: "305-P-2" });
  });

  it("drawing navigation: clicking a Related Engineering drawing opens Drawing Workspace scoped to this pump's own tag (no per-drawing lookup exists)", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("GA Drawing"));

    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: "305-P-2" });
  });

  // UI-D1.2 -- deleted: "pump navigation: clicking this pump's own identity
  // (crumb) opens Pump Workspace scoped to its own tag". This asserted the
  // old ChromeBar breadcrumb self-link (a clickable button showing the
  // pump's own tag, wired to onNavigate("pump", {selectId})). The Open
  // Design identity header's <h1> tag (AssetIdentityHeader.jsx) has no
  // click handler and Chief's approved reference has no self-navigating
  // crumb on the identity header -- confirmed via `grep '"pump"'` across
  // Pump.jsx/PumpOpenDesignView.jsx that no button renders this case
  // today. The underlying handleOpenEngineeringObject("PUMP"/"LIFECYCLE")
  // switch case in Pump.jsx is untouched and still reachable if a future
  // UI element wires it up; per this mission's "do not restore obsolete
  // DOM wrappers" / "do not modify production behavior merely to satisfy
  // an obsolete test" rules, no self-crumb button was reintroduced just to
  // keep this test green.

  it("invalid reference: a FAILURE timeline event has no target workspace and is not clickable", async () => {
    // MWO-LTSA-UI-V2-001 -- also appears in Recent Activities (getAllByText).
    // Neither instance is clickable (Recent Activities never renders a
    // button either), so every match must be a SPAN.
    await renderAndSelect(vi.fn());

    const failureNames = await screen.findAllByText("Failure MH-1");
    for (const name of failureNames) {
      expect(name.tagName).toBe("SPAN");
    }
  });

  it("pm navigation: a historically-imported PM occurrence with no pm_schedule_code/asset_code still navigates via its own pm_occurrence_code alone", async () => {
    // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- the exact shape a real
    // UNSCHEDULED::* historical record can have once other fields resolve
    // to nothing; pm_occurrence_code alone is sufficient real identity and
    // must never be treated as "no navigation" the way a missing
    // pm_schedule_code used to mean before this fix.
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click((await screen.findAllByText("PM Occurrence PM-NO-SCHEDULE"))[0]);

    expect(onNavigate).toHaveBeenCalledWith("pm", { occurrenceSelectId: "PM-NO-SCHEDULE", assetTag: undefined });
  });

  it("invalid reference: a PM timeline event with no pm_occurrence_code, pm_schedule_code, or asset_code at all does not navigate", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click((await screen.findAllByText("PM Occurrence PM-EMPTY"))[0]);

    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("timeline summary: a PM row shows status + completed checklist activities, never every temperature", async () => {
    await renderAndSelect(vi.fn());

    const pmRow = (await screen.findByText("PM Occurrence PM-1")).closest(".part-item");
    expect(pmRow.textContent).toContain("DONE");
    expect(pmRow.textContent).toContain("Flushing Line");
    expect(pmRow.textContent).toContain("Quench Line");
    expect(pmRow.textContent).not.toMatch(/°C|_temp_/);
  });

  it("timeline summary: an INSPECTION row shows operating state + finding, never a temperature value", async () => {
    await renderAndSelect(vi.fn());

    const cmonRow = (await screen.findByText("Condition Monitoring CMONR-1")).closest(".part-item");
    expect(cmonRow.textContent).toContain("Running");
    expect(cmonRow.textContent).toContain("Mechseal Bocor dari drain gland durasi 1/2 detik");
    expect(cmonRow.textContent).not.toMatch(/°C|_temp_/);
  });

  it("timeline summary: an INSPECTION row with no finding falls back to a disclosed leak status, never fabricated", async () => {
    await renderAndSelect(vi.fn());

    const cmonRow = (await screen.findByText("Condition Monitoring CMONR-2")).closest(".part-item");
    expect(cmonRow.textContent).toContain("Standby");
    expect(cmonRow.textContent).toContain("No Leak"); // R1C canonical label (DE=false, NDE=false)
  });

  it("same visit: a PM occurrence and an INSPECTION reading sharing the same date are both flagged Same Visit", async () => {
    await renderAndSelect(vi.fn());

    const pmRow = (await screen.findByText("PM Occurrence PM-1")).closest(".part-item");
    const cmonRow = (await screen.findByText("Condition Monitoring CMONR-1")).closest(".part-item");

    expect(pmRow.textContent).toContain("Same Visit • PM + Condition Monitoring");
    expect(cmonRow.textContent).toContain("Same Visit • PM + Condition Monitoring");
  });

  it("same visit: an INSPECTION reading on a date with no matching PM occurrence is NOT flagged Same Visit", async () => {
    await renderAndSelect(vi.fn());

    const cmonRow = (await screen.findByText("Condition Monitoring CMONR-2")).closest(".part-item");

    expect(cmonRow.textContent).not.toContain("Same Visit");
  });
});

// MWO-ASSET360-CARD-COMPLETENESS-R1 -- Current Seal/Current Installation
// (Overview tab) and Documents (Documents tab) now surface fields that
// were already mapped by pumpLifecycleMapping.js but never rendered
// (shaftSize/material/reportNo/sourceDocumentName) or were hardcoded to
// an unconditional empty string (Documents). No new API call, no new
// mapping -- see PumpOpenDesignView.jsx's own comments at each change.
describe("Asset360 card completeness (MWO-ASSET360-CARD-COMPLETENESS-R1)", () => {
  const CARD_TAG = "211-P-8A";

  const CARD_PUMPS = [
    {
      tag_number: CARD_TAG,
      name: "Debutanizer Feed Pump",
      area: "FRAKSINASI",
      manufacturer: null,
      pump_type: "BB",
      seal_type: "T48MP",
      location: null,
      status: "RUNNING",
      criticality: null,
    },
  ];

  function currentStateWith(overrides) {
    return {
      ...EMPTY_LIFECYCLE_DATA.current_state,
      ...overrides,
    };
  }

  async function renderCard(currentState) {
    getPumps.mockResolvedValue(CARD_PUMPS);
    getPumpOpenWorkOrders.mockResolvedValue({ success: true, openWO: 0, data: [] });
    getSeals.mockResolvedValue([]);
    getSealCompatibility.mockResolvedValue([]);
    postEngineeringAI.mockResolvedValue({
      summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
      risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
      token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
    });
    getPumpLifecycle.mockResolvedValue({
      success: true,
      tag_number: CARD_TAG,
      data: { ...EMPTY_LIFECYCLE_DATA, tag_number: CARD_TAG, current_state: currentState },
    });

    render(<Pump />);
    await screen.findByText(CARD_TAG);
    fireEvent.click(screen.getByText(CARD_TAG));
    await screen.findByRole("heading", { name: CARD_TAG });
  }

  const REAL_INSTALLATION = {
    installation_code: "INSTL-042-2026",
    report_no: "042/INSTL/TAP/06-2026",
    report_date: "2026-06-08",
    plant_equip_no: CARD_TAG,
    seal_code: null,
    seal_type: "T48MP",
    seal_manufacture: "John Crane",
    drawing_no: "E12894",
    source_document_name: "SCAN 042 INSTALLATION REPORT 211-P-8A.pdf",
  };

  const REAL_SEAL = {
    seal_code: null,
    seal_name: null,
    manufacturer: "John Crane",
    model: null,
    shaft_size: '3.1/2"',
    material: "QAR171/P",
    temperature_limit: null,
    pressure_limit: null,
    status: null,
    installation_code: "INSTL-042-2026",
    installed_at: "2026-06-08",
    source: "installation_report",
  };

  // A + B
  it("A/B: Current Seal card renders Shaft Size and Material", async () => {
    await renderCard(currentStateWith({ current_installation: REAL_INSTALLATION, current_seal: REAL_SEAL }));

    expect(await screen.findByText("Shaft Size")).toBeTruthy();
    expect(screen.getByText('3.1/2"')).toBeTruthy();
    expect(screen.getByText("Material")).toBeTruthy();
    expect(screen.getByText("QAR171/P")).toBeTruthy();

    // Pre-existing fields must still be present, unchanged (preserve rule).
    // getAllByText, not getByText: "Manufacturer" is also a real, unrelated
    // Asset Information label on this same page.
    expect(screen.getAllByText("Manufacturer").length).toBeGreaterThan(0);
    expect(screen.getAllByText("John Crane").length).toBeGreaterThan(0);
  });

  // C + D
  it("C/D: missing Shaft Size/Material fall back to the established Not Available label", async () => {
    const sealWithoutShaftOrMaterial = { ...REAL_SEAL, shaft_size: null, material: null };
    await renderCard(currentStateWith({ current_installation: REAL_INSTALLATION, current_seal: sealWithoutShaftOrMaterial }));

    expect(await screen.findByText("Shaft Size")).toBeTruthy();
    expect(screen.getByText("Material")).toBeTruthy();
    // Not Available appears for both, plus possibly other fields -- at
    // least 2 occurrences proves neither was silently dropped or fabricated.
    expect(screen.getAllByText("Not Available").length).toBeGreaterThanOrEqual(2);
  });

  // E + F
  it("E/F: Current Installation card renders Report No and Source Document", async () => {
    await renderCard(currentStateWith({ current_installation: REAL_INSTALLATION, current_seal: REAL_SEAL }));

    expect(await screen.findByText("Report No")).toBeTruthy();
    expect(screen.getByText("042/INSTL/TAP/06-2026")).toBeTruthy();
    expect(screen.getByText("Source Document")).toBeTruthy();
    expect(screen.getByText("SCAN 042 INSTALLATION REPORT 211-P-8A.pdf")).toBeTruthy();

    // Pre-existing fields must still be present, unchanged.
    expect(screen.getByText("Installation Code")).toBeTruthy();
    expect(screen.getByText("INSTL-042-2026")).toBeTruthy();
    expect(screen.getByText("Drawing No")).toBeTruthy();
    expect(screen.getByText("E12894")).toBeTruthy();
  });

  // G
  it("G: no installation at all is handled safely -- honest Not Available, no crash", async () => {
    await renderCard(currentStateWith({ current_installation: null, current_seal: null }));

    expect(await screen.findAllByText("Not Available")).toBeTruthy();
  });

  // H
  it("H: Documents tab shows the honest empty state when relatedEngineering.documents is []", async () => {
    await renderCard(currentStateWith({ current_installation: REAL_INSTALLATION, current_seal: REAL_SEAL }));
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    expect(await screen.findByText(/No document types available yet\./)).toBeTruthy();
  });

  // I
  it("I: Documents tab renders real document metadata and drops the unconditional empty string when documents exist", async () => {
    const lifecycleWithDocuments = currentStateWith({ current_installation: REAL_INSTALLATION, current_seal: REAL_SEAL });
    getPumps.mockResolvedValue(CARD_PUMPS);
    getPumpOpenWorkOrders.mockResolvedValue({ success: true, openWO: 0, data: [] });
    getSeals.mockResolvedValue([]);
    getSealCompatibility.mockResolvedValue([]);
    postEngineeringAI.mockResolvedValue({
      summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
      risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
      token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
    });
    getPumpLifecycle.mockResolvedValue({
      success: true,
      tag_number: CARD_TAG,
      data: {
        ...EMPTY_LIFECYCLE_DATA,
        tag_number: CARD_TAG,
        current_state: lifecycleWithDocuments,
        related_engineering: {
          ...EMPTY_LIFECYCLE_DATA.related_engineering,
          documents: [
            { document_code: "DOC-SEAL-DS-1", title: "Seal Datasheet T48MP", document_type: "DATASHEET", status: "APPROVED" },
          ],
        },
      },
    });

    render(<Pump />);
    await screen.findByText(CARD_TAG);
    fireEvent.click(screen.getByText(CARD_TAG));
    await screen.findByRole("heading", { name: CARD_TAG });
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    expect(await screen.findByText("Seal Datasheet T48MP")).toBeTruthy();
    expect(screen.getByText("DATASHEET")).toBeTruthy();
    expect(screen.queryByText(/No document types available yet\./)).toBeNull();
  });
});
