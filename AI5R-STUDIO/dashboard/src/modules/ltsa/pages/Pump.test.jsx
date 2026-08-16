import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Pump from "./Pump";
import {
  getPumps, getPumpOpenWorkOrders, getPumpLifecycle, getSeals, getSealCompatibility, postEngineeringAI,
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
// getPumpOpenWorkOrders stays -- it is a registry-list-level fetch
// (PumpRegistryTable's own openWO column, resolved for every row), not a
// lifecycle-detail concern, so it is unaffected by this MWO.
// MWO-LTSA-UI-V2-001 -- Seal & Inventory: getSeals()/getSealCompatibility()
// are the two already-existing endpoints Seal.jsx already fetches, now
// also fetched once (not per-pump) by Pump.jsx to enrich lifecycle's
// inventory array with real Type/Size + the full compatible-pump list. No
// new backend route -- see sealMapping.js's buildSealInventoryGroups().
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
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
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));

    expect(
      await screen.findByRole("heading", { name: "Cooling Water Circulation Pump" })
    ).toBeTruthy();
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

  it("navigates to Asset 360 already scoped to this pump when View History is clicked from the sticky Action Bar", async () => {
    loadPumps();
    const onNavigate = vi.fn();
    render(<Pump onNavigate={onNavigate} />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    // MWO-LTSA-050 -- "View History" moved from the old Quick Actions card
    // into the sticky Action Bar, matching Seal's own navigation-button
    // convention ("Buka Pump →", "Buka Drawing →") with a trailing arrow.
    fireEvent.click(await screen.findByRole("button", { name: "View History →" }));

    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "305-P-2" });
  });

  it("resolves openWO per pump via the canonical API", async () => {
    loadPumps();
    getPumpOpenWorkOrders.mockImplementation((tag) =>
      Promise.resolve({ success: true, tag_number: tag, openWO: tag === "641-P-5" ? 2 : 0, data: [] })
    );
    render(<Pump />);
    await screen.findByText("641-P-5");

    expect(getPumpOpenWorkOrders).toHaveBeenCalledWith("641-P-5");
    expect(screen.getByText("2")).toBeTruthy();
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
    await screen.findByRole("heading", { name: "Cooling Water Circulation Pump" });

    expect(getPumpLifecycle).toHaveBeenCalledWith("305-P-2");
    expect(await screen.findByText(/MH-101/)).toBeTruthy();
    expect(screen.getByText(/2026-06-02/)).toBeTruthy();
  });

  it("resolves Compatible Seals from lifecycle.related_engineering.inventory, lazily for the selected pump only", async () => {
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
            { seal_code: "SC-011", quantity_on_hand: 4, reorder_point: 2, location: "Warehouse A" },
          ],
        },
      },
    });
    render(<Pump />);
    await screen.findByText("305-P-2");

    expect(getPumpLifecycle).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "Cooling Water Circulation Pump" });

    expect(getPumpLifecycle).toHaveBeenCalledWith("305-P-2");
    // MWO-LTSA-065 -- lifecycle's inventory shape has no part_name (only
    // pumpMapping.js/withResolvedSpareParts's old shape did), so the
    // Compatible Seals item name is the real seal_code.
    expect(await screen.findAllByText(/SC-011/)).not.toHaveLength(0);
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
            { seal_code: "SC-011", quantity_on_hand: 4, reorder_point: 2, location: "Warehouse A" },
          ],
        },
      },
    });
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "Cooling Water Circulation Pump" });

    expect(await screen.findByText(/MH-101/)).toBeTruthy();
    expect(screen.getAllByText(/SC-011/).length).toBeGreaterThan(0);
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
        payload: { pm_occurrence_code: "PM-1", pm_schedule_code: "PMS-1", asset_code: "305-P-2" },
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
        // Deliberately no pm_schedule_code and no asset_code -- an
        // invalid/incomplete reference this MWO's "never guess" rule must
        // leave non-navigating rather than crashing or fabricating a link.
        payload: { pm_occurrence_code: "PM-NO-SCHEDULE" },
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
    loadNav();
    render(<Pump onNavigate={onNavigate} />);
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByRole("heading", { name: "Cooling Water Circulation Pump" });
  }

  it("installation navigation: clicking an INSTALLATION timeline event opens Installation Workspace scoped to that report", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("Installation INSTL-001-2026"));

    expect(onNavigate).toHaveBeenCalledWith("installation", { selectId: "INSTL-001-2026" });
  });

  it("pm navigation: clicking a PM timeline event opens PM Workspace via the occurrence's own pm_schedule_code", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("PM Occurrence PM-1"));

    expect(onNavigate).toHaveBeenCalledWith("pm", { selectId: "PMS-1" });
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
    // timeline events, so it now also appears (non-clickable) in the
    // Inspector Rail's Recent Activities -- getAllByText, not getByText.
    // Index [0] is the main Timeline section's own clickable item (DOM
    // order: <main> precedes <aside class="inspector-rail">).
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click((await screen.findAllByText("Work Order WO-1"))[0]);

    expect(onNavigate).toHaveBeenCalledWith("workorder", { selectId: "WO-1" });
  });

  it("drawing navigation: clicking a Related Engineering drawing opens Drawing Workspace scoped to this pump's own tag (no per-drawing lookup exists)", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByText("GA Drawing"));

    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: "305-P-2" });
  });

  it("pump navigation: clicking this pump's own identity (crumb) opens Pump Workspace scoped to its own tag", async () => {
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click(await screen.findByRole("button", { name: "305-P-2" }));

    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "305-P-2" });
  });

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

  it("invalid reference: a PM timeline event missing both pm_schedule_code and asset_code does not navigate", async () => {
    // MWO-LTSA-UI-V2-001 -- also appears (non-clickable) in Recent
    // Activities -- getAllByText, click index [0] (the main Timeline
    // section's own item).
    const onNavigate = vi.fn();
    await renderAndSelect(onNavigate);

    fireEvent.click((await screen.findAllByText("PM Occurrence PM-NO-SCHEDULE"))[0]);

    expect(onNavigate).not.toHaveBeenCalled();
  });
});
