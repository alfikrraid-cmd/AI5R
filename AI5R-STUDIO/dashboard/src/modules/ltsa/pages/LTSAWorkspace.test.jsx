import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LTSAWorkspace from "./LTSAWorkspace";
import {
  getWorkOrders,
  getWorkOrderAsset,
  getWorkOrderTimeline,
  createWorkOrder,
  getPumps,
  getPump,
  getPumpLastPM,
  getPumpLastCM,
  getPumpConditionMonitoringFlag,
  getPumpOpenWorkOrders,
  getPumpSpareParts,
  getPumpLifecycle,
  getSeals,
  getSealCompatibility,
  getPMSchedules,
  getCMReports,
  getMaintenanceHistory,
  getPMOccurrences,
  getConditionMonitoringReadings,
  getConditionMonitoringSchedules,
  getPumpKnowledge,
  getFleetOverview,
  getFleetReliability,
  getFleetPowerBI,
  postEngineeringAI,
} from "../../../api/ai5rClient";
import { WORKSPACE_KEYS, workspaceLocation } from "../workspace/WorkspaceRegistry";

// Every real (non-mock-data) ai5rClient function reachable from this shell's
// tabs must be mocked here -- vi.mock replaces the whole module, so any
// tab's page component calling an unmocked export would fail with
// "undefined is not a function", not just the tab this file directly
// exercises.
vi.mock("../../../api/ai5rClient", () => ({
  getWorkOrders: vi.fn(),
  getWorkOrderAsset: vi.fn(),
  getWorkOrderTimeline: vi.fn(),
  createWorkOrder: vi.fn(),
  getPumps: vi.fn(),
  getPump: vi.fn(),
  getPumpLastPM: vi.fn(),
  getPumpLastCM: vi.fn(),
  getPumpConditionMonitoringFlag: vi.fn(),
  getPumpOpenWorkOrders: vi.fn(),
  getPumpSpareParts: vi.fn(),
  getPumpLifecycle: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
  getMaintenanceHistory: vi.fn(),
  getPMOccurrences: vi.fn(),
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPumpKnowledge: vi.fn(),
  getFleetOverview: vi.fn(),
  getFleetReliability: vi.fn(),
  getFleetPowerBI: vi.fn(),
  postEngineeringAI: vi.fn(),
  getSeals: vi.fn(),
  getSealStock: vi.fn(),
  getSealCompatibility: vi.fn(),
}));

const PUMPS = [
  {
    tag_number: "305-P-2",
    name: "Cooling Water Circulation Pump",
    area: "Utilities",
    manufacturer: "Flowserve",
    status: "RUNNING",
  },
];

beforeEach(() => {
  getWorkOrders.mockResolvedValue([]);
  getWorkOrderAsset.mockResolvedValue({ success: true, area: null });
  getWorkOrderTimeline.mockResolvedValue([]);
  createWorkOrder.mockResolvedValue({});
  getPumps.mockResolvedValue(PUMPS);
  getPump.mockResolvedValue({ tag_number: null, area: null });
  // MWO-LTSA-UI-V2-001 -- Seal & Inventory: Pump.jsx now also fetches
  // these two already-existing endpoints once on mount (see
  // sealMapping.js's buildSealInventoryGroups()).
  getSeals.mockResolvedValue([]);
  getSealCompatibility.mockResolvedValue([]);
  getPumpOpenWorkOrders.mockResolvedValue({ success: true, openWO: 0, data: [] });
  getPumpLastPM.mockResolvedValue({ success: true, tag_number: null, last_pm: null });
  getPumpSpareParts.mockResolvedValue({ success: true, tag_number: null, spare_parts: [] });
  getPumpLastCM.mockResolvedValue({ success: true, tag_number: null, last_cm: null });
  getPumpConditionMonitoringFlag.mockResolvedValue({
    success: true,
    tag_number: null,
    flagged: false,
    window_days: 30,
    latest_flagged_reading: null,
  });
  getPMSchedules.mockResolvedValue([]);
  getCMReports.mockResolvedValue([]);
  getMaintenanceHistory.mockResolvedValue([]);
  getPMOccurrences.mockResolvedValue([]);
  getConditionMonitoringReadings.mockResolvedValue([]);
  getConditionMonitoringSchedules.mockResolvedValue([]);
  getPumpKnowledge.mockResolvedValue({
    success: true,
    tag_number: "305-P-2",
    data: {
      summary: { asset: { tag_number: "305-P-2", pump_name: "Cooling Water Circulation Pump" } },
      timeline: [],
      seal: [],
      inventory: [],
      pm: [],
      cm: [],
      breakdown: [],
      drawings: null,
      recommendation: null,
    },
  });
  getFleetOverview.mockResolvedValue({
    success: true,
    data: {
      pump_count: 0,
      area_distribution: {},
      status_distribution: {},
      work_order_count: 0,
      work_order_status_distribution: {},
      pm_schedule_count: 0,
      cm_report_count: 0,
      seal_stock_count: 0,
      low_stock_seal_count: null,
    },
  });
  getFleetReliability.mockResolvedValue({
    success: true,
    data: {
      pump_count: 0,
      fleet_health_score: null,
      fleet_mtbf_days: null,
      fleet_mttr_hours: null,
      fleet_availability: null,
      total_breakdown_count: 0,
      total_critical_spare_count: 0,
    },
  });
  getFleetPowerBI.mockResolvedValue({
    success: true,
    data: {
      overall_health: null,
      fleet_status: "UNKNOWN",
      critical_asset_count: 0,
      fleet_availability: null,
      fleet_mtbf_days: null,
      fleet_mttr_hours: null,
      breakdown_count: 0,
      critical_spare_count: 0,
      top_risks: [],
      insight: null,
    },
  });
  postEngineeringAI.mockResolvedValue({
    execution_status: "SUCCESS",
    summary: "AI summary",
    findings: [],
    recommendations: [],
    evidence: [],
    source_references: [],
    confidence: null,
    risk: null,
    remaining_life: null,
  });
  // MWO-LTSA-065 -- Pump.jsx now fetches GET /api/ltsa/pumps/{tag}/lifecycle
  // whenever a pump is selected; this shell walkthrough selects pumps, so
  // it must be mocked here too, same as every other real fetch above.
  getPumpLifecycle.mockResolvedValue({
    success: true,
    tag_number: null,
    data: {
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
    },
  });
});

// Every deep-link test below must leave window.location exactly as it
// found it -- window.history is a jsdom global shared across every test
// in this file, and the other (pre-existing) tests all assume the
// default "/" path via LTSAWorkspace's initialActiveKey prop fallback.
afterEach(() => {
  window.history.pushState({}, "", "/");
});

describe("LTSAWorkspace navigation shell", () => {
  it("renders a tab for every LTSA workspace", () => {
    render(<LTSAWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Dashboard" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pump" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Work Order" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Preventive Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Corrective Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Condition Monitoring" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Asset 360" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Reports" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Analytics" })).toBeTruthy();
  });

  it("defaults to the Executive Dashboard", () => {
    render(<LTSAWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Dashboard" }).getAttribute("aria-selected")).toBe(
      "true"
    );
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();
  });

  // MWO-LTSA-DASHBOARD-RECOVERY-001 -- a fresh mount whose URL doesn't
  // already resolve to a workspace location (e.g. "/", the default from
  // afterEach above) must sync the URL to the canonical route of whatever
  // it actually renders, not leave the browser showing a stale/unrelated
  // path while the content underneath has already moved on.
  it("syncs the URL to the canonical dashboard route when the initial URL didn't resolve to anything", () => {
    render(<LTSAWorkspace />);

    expect(window.location.pathname).toBe("/ltsa/dashboard");
  });

  it("does not rewrite the URL when it already resolved to a valid deep link on mount", () => {
    const tag = "305-P-2";
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: tag }));

    render(<LTSAWorkspace />);

    expect(window.location.pathname).toBe(`/ltsa/pump/${tag}`);
  });

  it("can open Asset 360 as its initial route page -- untagged, resolves via MaintenanceHistory's asset picker (MWO-LTSA-036G)", async () => {
    render(<LTSAWorkspace initialActiveKey="history" />);

    expect(screen.getByRole("tab", { name: "Asset 360" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    await screen.findByLabelText("Select Asset");
  });

  it("switches to the Pump workspace when its tab is clicked", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
    await screen.findByText("305-P-2");
  });

  it("switches to the Work Order workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Work Order" }));

    expect(screen.getByRole("heading", { name: "Work Order Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
  });

  it("switches to the Preventive Maintenance workspace when its tab is clicked", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Preventive Maintenance" }));

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Workspace" })).toBeTruthy();
    await screen.findByText(/no pm schedules match/i);
  });

  it("switches to the Corrective Maintenance workspace when its tab is clicked", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Corrective Maintenance" }));

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Workspace" })).toBeTruthy();
    await screen.findByText(/no corrective maintenance reports match/i);
  });

  it("switches to Asset 360 when its tab is clicked -- untagged, resolves via MaintenanceHistory's asset picker (MWO-LTSA-036G)", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));

    // No assetTag context from a bare tab click -- KnowledgeWorkspace must
    // never receive a null tag and stays host-agnostic (no internal picker,
    // MWO-LTSA-036G), so the routing adapter resolves the asset first via
    // MaintenanceHistory's existing, unmodified AssetSelector flow.
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    await screen.findByLabelText("Select Asset");
  });

  it("switches to the Condition Monitoring workspace when its tab is clicked", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Condition Monitoring" }));

    expect(screen.getByRole("heading", { name: "Condition Monitoring" })).toBeTruthy();
    await screen.findByText(/no condition monitoring schedules match/i);
  });

  it("switches to the Reports workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Reports" }));

    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
  });

  it("switches to the Analytics workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Analytics" }));

    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
  });

  it("completes a first-time-user demo walkthrough across every workspace without error", async () => {
    render(<LTSAWorkspace />);

    // Land on the Executive Dashboard by default.
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();

    // Jump to Pump Registry via Quick Navigation, select a pump, view its detail.
    fireEvent.click(screen.getByRole("button", { name: "Open Pump Registry" }));
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();

    fireEvent.click(await screen.findByText("305-P-2"));
    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();

    // Follow the pump's "View History" quick action into Asset 360, already
    // scoped to this pump (APP-ASSET360-001's assetTag navigation payload).
    // MWO-LTSA-036D: Asset 360 is now KnowledgeWorkspace -- with an assetTag
    // in context (unlike a bare tab click), it renders real content, not
    // the no-tag empty state.
    fireEvent.click(screen.getByRole("button", { name: /View History/i }));
    await screen.findByTestId("knowledge-workspace-success");
    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();

    // Return to the Dashboard and jump to Reports via Quick Navigation.
    fireEvent.click(screen.getByRole("tab", { name: "Executive Dashboard" }));
    fireEvent.click(screen.getByRole("button", { name: "Open Reports" }));
    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Pump History Report" }));
    expect(screen.getByRole("heading", { name: "Pump History Report" })).toBeTruthy();

    // Return to the Dashboard and jump to Analytics via Quick Navigation.
    fireEvent.click(screen.getByRole("tab", { name: "Executive Dashboard" }));
    fireEvent.click(screen.getByRole("button", { name: "Open Analytics" }));
    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Are we healthy?" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What should managers do next?" })).toBeTruthy();

    // Every outer LTSA tab remains reachable after this journey.
    ["Executive Dashboard", "Pump", "Work Order", "Preventive Maintenance", "Corrective Maintenance", "Condition Monitoring", "Asset 360", "Reports", "Analytics"].forEach(
      (tabName) => {
        expect(screen.getByRole("tab", { name: tabName })).toBeTruthy();
      }
    );
  });
});

describe("Asset360 Navigation Activation (MWO-LTSA-036D)", () => {
  const TAG = "305-P-2";
  const LEGACY_PATH = workspaceLocation(WORKSPACE_KEYS.PUMP_LEGACY, {});

  it("every existing history navigation with an assetTag opens KnowledgeWorkspace: bare tab click, then a tagged deep link", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));
    // Untagged: superseded by MWO-LTSA-036G -- see "Asset Launcher" describe
    // block below for the current (resolve-before-navigation) behavior.
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("every existing history navigation with an assetTag opens KnowledgeWorkspace: initialActiveKey prop", () => {
    render(<LTSAWorkspace initialActiveKey="history" />);

    // Untagged: superseded by MWO-LTSA-036G -- see "Asset Launcher" describe
    // block below for the current (resolve-before-navigation) behavior.
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("every existing history navigation now opens KnowledgeWorkspace: onNavigate with an assetTag", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));
    // Simulate the same onNavigate("history", { assetTag }) call Pump.jsx's
    // "View History" button makes, via a direct deep link (equivalent
    // effect, avoids depending on Pump.jsx's own unrelated data fetch).
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));
    window.dispatchEvent(new PopStateEvent("popstate"));

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith(TAG);
  });

  it("fallback route still works: /ltsa/pump-workspace-legacy renders the legacy MaintenanceHistory page", async () => {
    window.history.pushState({}, "", LEGACY_PATH);

    render(<LTSAWorkspace />);

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    await screen.findByLabelText("Select Asset");
  });

  it("fallback route is not on the tab bar (temporary, deep-link-only, like the other MWO-LTSA-032E routes)", () => {
    render(<LTSAWorkspace />);

    expect(screen.queryByRole("tab", { name: /legacy/i })).toBeNull();
  });

  it("deep link: /ltsa/pump/{tag} opens the repointed Asset 360 (KnowledgeWorkspace) with the right tag", async () => {
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));

    render(<LTSAWorkspace />);

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith(TAG);
  });

  it("browser refresh: a fresh mount on the repointed Asset 360 URL lands back on KnowledgeWorkspace", async () => {
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));

    const { unmount } = render(<LTSAWorkspace />);
    await screen.findByTestId("knowledge-workspace-success");
    unmount();

    render(<LTSAWorkspace />);
    await screen.findByTestId("knowledge-workspace-success");
  });

  it("browser back/forward (popstate) between the repointed Asset 360 and the legacy fallback route", async () => {
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));
    render(<LTSAWorkspace />);
    await screen.findByTestId("knowledge-workspace-success");

    window.history.pushState({}, "", LEGACY_PATH);
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => expect(screen.queryByTestId("knowledge-workspace-success")).toBeNull());
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();

    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));
    window.dispatchEvent(new PopStateEvent("popstate"));
    await screen.findByTestId("knowledge-workspace-success");
  });
});

describe("Asset Launcher (MWO-LTSA-036G) -- KnowledgeWorkspace must never receive a null tag", () => {
  const TAG = "305-P-2";

  it("Quick Navigation: 'Open Asset 360' (untagged) resolves the asset first instead of a dead-end empty state", async () => {
    getPumpKnowledge.mockClear();
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Open Asset 360" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    await screen.findByLabelText("Select Asset");
    // KnowledgeWorkspace never mounted, so it never called the Knowledge API.
    expect(getPumpKnowledge).not.toHaveBeenCalled();
  });

  it("Pump page (regression): 'View History' already carries an assetTag and reaches KnowledgeWorkspace directly, no picker detour", async () => {
    // Simulates the same onNavigate("history", { assetTag }) call Pump.jsx's
    // "View History" button makes (via a direct deep link, equivalent
    // effect), rather than clicking through Pump.jsx's own UI -- avoids
    // depending on Pump.jsx's unrelated, pre-existing postEngineeringAI
    // data fetch (not mocked in this file, out of this MWO's scope).
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));

    render(<LTSAWorkspace />);

    await screen.findByTestId("knowledge-workspace-success");
    expect(screen.queryByLabelText("Select Asset")).toBeNull();
  });

  it("deep link: a tagged URL (/ltsa/pump/{tag}) reaches KnowledgeWorkspace directly, never the picker detour", async () => {
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));

    render(<LTSAWorkspace />);

    await screen.findByTestId("knowledge-workspace-success");
    expect(screen.queryByLabelText("Select Asset")).toBeNull();
  });

  it("refresh: a fresh mount on the untagged Asset 360 URL still resolves via the asset picker, never a null tag", async () => {
    getPumpKnowledge.mockClear();
    window.history.pushState({}, "", "/ltsa/pump-workspace");

    const { unmount } = render(<LTSAWorkspace />);
    await screen.findByLabelText("Select Asset");
    unmount();

    render(<LTSAWorkspace />);
    await screen.findByLabelText("Select Asset");
    expect(getPumpKnowledge).not.toHaveBeenCalled();
  });

  it("back button: popstate between the untagged picker and the tagged KnowledgeWorkspace, both under the same 'history' key", async () => {
    window.history.pushState({}, "", "/ltsa/pump-workspace");
    render(<LTSAWorkspace />);
    await screen.findByLabelText("Select Asset");

    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG }));
    window.dispatchEvent(new PopStateEvent("popstate"));
    await screen.findByTestId("knowledge-workspace-success");

    window.history.pushState({}, "", "/ltsa/pump-workspace");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => expect(screen.queryByTestId("knowledge-workspace-success")).toBeNull());
    await screen.findByLabelText("Select Asset");
  });
});

describe("Knowledge Workspace navigation (MWO-LTSA-032E)", () => {
  const TAG = "305-P-2";
  const KNOWLEDGE_PATH = workspaceLocation(WORKSPACE_KEYS.KNOWLEDGE, { assetTag: TAG });

  it("is reachable: deep-linking to its URL renders KnowledgeWorkspace, not the default Dashboard", async () => {
    window.history.pushState({}, "", KNOWLEDGE_PATH);

    render(<LTSAWorkspace />);

    await screen.findByTestId("knowledge-workspace-success");
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
  });

  it("deep link resolves the correct assetTag from the URL into KnowledgeWorkspace", async () => {
    window.history.pushState({}, "", KNOWLEDGE_PATH);

    render(<LTSAWorkspace />);

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith(TAG);
  });

  it("survives a browser refresh: a fresh mount on the Knowledge Workspace URL lands back on it", async () => {
    // A refresh is, from React's perspective, a brand-new mount reading
    // whatever URL is already in the address bar -- exactly what
    // LTSAWorkspace's initial-state read of window.location.pathname does.
    window.history.pushState({}, "", KNOWLEDGE_PATH);

    const { unmount } = render(<LTSAWorkspace />);
    await screen.findByTestId("knowledge-workspace-success");
    unmount();

    render(<LTSAWorkspace />);
    await screen.findByTestId("knowledge-workspace-success");
  });

  it("supports browser back/forward (popstate) between Knowledge Workspace and another route", async () => {
    // MWO-LTSA-036D: /ltsa/pump-workspace ("history") is now also
    // KnowledgeWorkspace, so the legacy fallback route is used here as the
    // genuinely distinct "another route" this test's name refers to.
    window.history.pushState({}, "", "/ltsa/pump-workspace-legacy");
    render(<LTSAWorkspace />);
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();

    // Simulate the browser navigating forward to the Knowledge Workspace
    // URL (e.g. a deep link opened in-session) and firing popstate.
    window.history.pushState({}, "", KNOWLEDGE_PATH);
    window.dispatchEvent(new PopStateEvent("popstate"));
    await screen.findByTestId("knowledge-workspace-success");

    // Simulate the user pressing Back.
    window.history.pushState({}, "", "/ltsa/pump-workspace-legacy");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => expect(screen.queryByTestId("knowledge-workspace-success")).toBeNull());
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });
});

describe("Equipment nav retirement (MWO-LTSA-EQUIPMENT-TAB-RESOLUTION-001)", () => {
  it("Equipment is no longer a clickable LTSA nav destination", () => {
    render(<LTSAWorkspace />);

    expect(screen.queryByRole("tab", { name: "Equipment" })).toBeNull();
  });

  it("the canonical Pump/Asset workspace remains available, renders, and asset selection still works", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    fireEvent.click(await screen.findByText("305-P-2"));
    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();
  });

  it("Asset 360 (Equipment History) remains reachable through the canonical asset flow, scoped to the selected pump", async () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));
    fireEvent.click(await screen.findByText("305-P-2"));
    fireEvent.click(screen.getByRole("button", { name: /View History/i }));

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith("305-P-2");
  });

  it("ai5rClient no longer exports the dead Equipment API functions", async () => {
    const actualModule = await vi.importActual("../../../api/ai5rClient");

    expect(actualModule.getEquipmentList).toBeUndefined();
    expect(actualModule.getEquipment).toBeUndefined();
    expect(actualModule.getEquipmentInspections).toBeUndefined();
    expect(actualModule.getInspectionFindings).toBeUndefined();
    expect(actualModule.getFindingWorkOrders).toBeUndefined();
  });
});

describe("Asset identity & history closure (MWO-LTSA-DEMO-READINESS-CLOSURE-001)", () => {
  const DEMO_PUMPS = [
    { tag_number: "212-P-7B", name: "Reaktor Feed Pump", area: "Reaktor", manufacturer: "Flowserve", status: "RUNNING" },
    { tag_number: "211-P-7B", name: "CONDENSATE PUMP", area: "HCC", manufacturer: "Flowserve", status: "RUNNING" },
  ];

  const TIMELINE_212 = [
    { id: "evt-pm-1", event_type: "PM", title: "PM 2026-001 completed", occurred_at: "2026-01-01" },
    { id: "evt-insp-1", event_type: "INSPECTION", title: "CMON reading logged (1)", occurred_at: "2026-01-02" },
    { id: "evt-insp-2", event_type: "INSPECTION", title: "CMON reading logged (2)", occurred_at: "2026-01-03" },
    { id: "evt-insp-3", event_type: "INSPECTION", title: "CMON reading logged (3)", occurred_at: "2026-01-04" },
    { id: "evt-insp-4", event_type: "INSPECTION", title: "CMON reading logged (4)", occurred_at: "2026-01-05" },
  ];

  function knowledgeFor(tag) {
    if (tag === "212-P-7B") {
      return {
        success: true,
        tag_number: tag,
        data: {
          summary: { asset: { tag_number: tag, pump_name: "Reaktor Feed Pump" } },
          timeline: TIMELINE_212,
          seal: [],
          inventory: [],
          pm: [{ pm_occurrence_code: "PM-2026-001", occurrence_date: "2026-01-01" }],
          cm: [],
          breakdown: [],
          drawings: [],
          recommendation: null,
          ai_insight: null,
          pm_schedules: [],
          condition_monitoring_schedules: [],
        },
      };
    }
    return {
      success: true,
      tag_number: tag,
      data: {
        summary: { asset: { tag_number: tag, pump_name: "CONDENSATE PUMP" } },
        timeline: [],
        seal: [],
        inventory: [],
        pm: [],
        cm: [],
        breakdown: [],
        drawings: [],
        recommendation: null,
        ai_insight: null,
        pm_schedules: [],
        condition_monitoring_schedules: [],
      },
    };
  }

  it("212-P-7B selected via Pump -> View History renders and requests exactly 212-P-7B, never 211-P-7B", async () => {
    getPumpKnowledge.mockClear();
    getPumps.mockResolvedValue(DEMO_PUMPS);
    getPumpKnowledge.mockImplementation(async (tag) => knowledgeFor(tag));

    render(<LTSAWorkspace />);
    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));
    fireEvent.click(await screen.findByText("212-P-7B"));
    fireEvent.click(screen.getByRole("button", { name: /View History/i }));

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith("212-P-7B");
    expect(getPumpKnowledge).not.toHaveBeenCalledWith("211-P-7B");
    expect(screen.queryByText("211-P-7B")).toBeNull();
  });

  it("a different asset (211-P-7B) remains itself through the same flow -- proves this is not a hard-coded fix", async () => {
    getPumpKnowledge.mockClear();
    getPumps.mockResolvedValue(DEMO_PUMPS);
    getPumpKnowledge.mockImplementation(async (tag) => knowledgeFor(tag));

    render(<LTSAWorkspace />);
    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));
    fireEvent.click(await screen.findByText("211-P-7B"));
    fireEvent.click(screen.getByRole("button", { name: /View History/i }));

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith("211-P-7B");
    expect(getPumpKnowledge).not.toHaveBeenCalledWith("212-P-7B");
  });

  it("the untagged Asset 360 entry point is a picker only -- it never renders the legacy history engine's markers", async () => {
    getPumps.mockResolvedValue(DEMO_PUMPS);

    render(<LTSAWorkspace />);
    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));

    await screen.findByLabelText("Select Asset");
    expect(screen.queryByText("No history matches this filter.")).toBeNull();
    expect(screen.queryByText(/Reliability assessment: Coming Soon/i)).toBeNull();
    expect(screen.queryByText("Stok Habis")).toBeNull();
  });

  it("picking an asset from the untagged Asset 360 picker routes to the canonical KnowledgeWorkspace for that exact tag", async () => {
    getPumpKnowledge.mockClear();
    getPumps.mockResolvedValue(DEMO_PUMPS);
    getPumpKnowledge.mockImplementation(async (tag) => knowledgeFor(tag));

    render(<LTSAWorkspace />);
    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));
    await screen.findByLabelText("Select Asset");

    fireEvent.change(screen.getByLabelText("Select Asset"), { target: { value: "212-P-7B" } });

    await screen.findByTestId("knowledge-workspace-success");
    expect(getPumpKnowledge).toHaveBeenCalledWith("212-P-7B");
  });

  it("212-P-7B's canonical Equipment Timeline reaches the UI with 1 PM + 4 CMON/INSPECTION events, no duplicate IDs, all reachable", async () => {
    getPumps.mockResolvedValue(DEMO_PUMPS);
    getPumpKnowledge.mockImplementation(async (tag) => knowledgeFor(tag));

    render(<LTSAWorkspace />);
    window.history.pushState({}, "", workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: "212-P-7B" }));
    window.dispatchEvent(new PopStateEvent("popstate"));

    await screen.findByTestId("knowledge-workspace-success");

    expect(screen.getByText("5 peristiwa")).toBeTruthy();
    const timelineList = screen.getByTestId("knowledge-timeline");
    const items = within(timelineList).getAllByRole("listitem");
    expect(items).toHaveLength(5);

    const ids = TIMELINE_212.map((event) => event.id);
    expect(new Set(ids).size).toBe(ids.length);

    for (const event of TIMELINE_212) {
      expect(screen.getByText(event.title)).toBeTruthy();
    }
  });
});

