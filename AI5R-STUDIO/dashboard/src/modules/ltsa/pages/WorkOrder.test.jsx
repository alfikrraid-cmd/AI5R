import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import WorkOrder from "./WorkOrder";
import {
  createWorkOrder,
  getWorkOrders,
  getWorkOrderAsset,
  getWorkOrderTimeline,
  postEngineeringAI,
  getPMSchedules,
  getCMReports,
} from "../../../api/ai5rClient";

// postEngineeringAI stubbed here only because WorkOrder.jsx now calls it
// (MWO-LTSA-SEAL-AI-001 follow-on: Work Order Workspace Engineering AI
// integration) -- no existing assertion in this file was changed to
// accommodate that; every test below verifies exactly what it verified
// before.
// getPMSchedules/getCMReports stubbed here only because
// WorkOrderOpenDesignView's Related Engineering section (MWO-LTSA-055)
// fetches them once a work order with a resolved equipmentTag is
// selected, the same already-wired calls Seal.jsx/PM.jsx use.
vi.mock("../../../api/ai5rClient", () => ({
  createWorkOrder: vi.fn(),
  getWorkOrders: vi.fn(),
  getWorkOrderAsset: vi.fn(),
  getWorkOrderTimeline: vi.fn(),
  postEngineeringAI: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
}));

const WORK_ORDERS = [
  {
    work_order_code: "WO-1001",
    title: "Seal replacement — repeat failures",
    asset_code: "641-P-5",
    asset_type: "PUMP",
    description: "Third seal failure in 90 days.",
    priority: "CRITICAL",
    status: "OPEN",
    assigned_to: "Dedi Kurniawan",
    work_type: "CM",
    due_date: "2026-07-21",
    created_at: "2026-07-18",
  },
  {
    work_order_code: "WO-1002",
    title: "Quarterly vibration survey",
    asset_code: "211-P-1A",
    asset_type: "PUMP",
    description: "Routine quarterly vibration baseline survey per PM schedule.",
    priority: "MEDIUM",
    status: "IN_PROGRESS",
    assigned_to: "Sari Wulandari",
    work_type: "PM",
    due_date: "2026-07-24",
    created_at: "2026-07-10",
  },
  {
    work_order_code: "WO-1008",
    title: "Monthly churn test",
    asset_code: "533-P-1",
    asset_type: "PUMP",
    description: "Monthly fire water jockey pump churn test.",
    priority: "HIGH",
    status: "COMPLETED",
    assigned_to: "Bagus Setiawan",
    work_type: "PM",
    due_date: "2026-07-01",
    created_at: "2026-06-28",
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

function loadWorkOrders(records = WORK_ORDERS) {
  getWorkOrders.mockResolvedValue(records);
  postEngineeringAI.mockResolvedValue({
    summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
    risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
    token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
  });
  getWorkOrderAsset.mockResolvedValue({
    success: true,
    message: "Asset area resolved",
    asset_code: null,
    asset_type: "PUMP",
    area: "Unit 1",
  });
  getWorkOrderTimeline.mockResolvedValue([]);
  getPMSchedules.mockResolvedValue([]);
  getCMReports.mockResolvedValue([]);
}

// UI-D2A.1 -- the registry now renders two representations of the same
// data simultaneously (desktop table + mobile card list, CSS-gated in
// WorkOrder.css; jsdom applies no CSS, so both are always in the DOM).
// Every WO ID/title/badge that used to be a single unambiguous match is
// now two -- scope existence/click queries to the always-present table
// (the desktop-primary representation) so these tests keep asserting the
// same real behavior without depending on which viewport-only element
// happens to render.
// Async: the table doesn't exist until the initial getWorkOrders() fetch
// resolves (the component starts in a loading state), so this must use
// findByRole (auto-retrying), never getByRole, or callers would race it.
function registryTable() {
  return screen.findByRole("table");
}

describe("Work Order workspace page", () => {
  it("renders the page header", async () => {
    // UI-D2A -- page title text changed to "WORK ORDERS" per Chief's
    // approved reference (WorkOrder.css/.jsx); same page, new copy.
    loadWorkOrders();
    render(<WorkOrder />);

    expect(screen.getByRole("heading", { name: "WORK ORDERS" })).toBeTruthy();
    await within(await registryTable()).findByText("WO-1001");
  });

  it("renders a loading state before the API resolves", () => {
    getWorkOrders.mockReturnValue(new Promise(() => {}));
    render(<WorkOrder />);

    expect(screen.getByText("Loading work orders...")).toBeTruthy();
  });

  it("renders list API errors without fallback mock data", async () => {
    getWorkOrders.mockRejectedValue(new Error("API unavailable"));
    render(<WorkOrder />);

    expect(await screen.findByText("Work orders could not be loaded.")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
  });

  it("renders every work order from the canonical API in the registry table", async () => {
    loadWorkOrders();
    render(<WorkOrder />);

    for (const workOrder of WORK_ORDERS) {
      expect(await within(await registryTable()).findByText(workOrder.work_order_code)).toBeTruthy();
    }
    expect(getWorkOrders).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the detail panel before any work order is selected", async () => {
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1001");

    expect(screen.getByText(/no work order selected/i)).toBeTruthy();
  });

  it("shows the selected work order's detail when a registry row is clicked", async () => {
    // UI-D2A -- identity header's <h1> is the work order's ID; title is
    // adjacent subtitle text (AssetIdentityHeader.jsx), same convention
    // as Pump's tag/Seal's code.
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1002");

    fireEvent.click(within(await registryTable()).getByText("WO-1002"));

    expect(await screen.findByRole("heading", { name: "WO-1002" })).toBeTruthy();
    expect(screen.getAllByText("Quarterly vibration survey").length).toBeGreaterThan(0);
    expect(getWorkOrderTimeline).toHaveBeenCalledWith("WO-1002");
  });

  it("filters the registry table by search text", async () => {
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1001");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "vibration" } });

    expect(within(await registryTable()).getByText("WO-1002")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
  });

  it("filters the registry table by status", async () => {
    // UI-D2A -- Priority/Area filters added alongside Status, so the
    // combobox query must be scoped by its accessible name.
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1001");

    fireEvent.change(screen.getByRole("combobox", { name: "Filter by status" }), { target: { value: "COMPLETED" } });

    expect(within(await registryTable()).getByText("WO-1008")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
  });

  it("shows an empty state in the registry when no work order matches the search", async () => {
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1001");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-work-order-xyz" } });

    expect(screen.getByText(/no work orders match/i)).toBeTruthy();
  });

  it("opens the Create Work Order modal when the header action is clicked", async () => {
    loadWorkOrders();
    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1001");

    fireEvent.click(screen.getByRole("button", { name: "+ Create Work Order" }));

    expect(screen.getByRole("heading", { name: "Create Work Order" })).toBeTruthy();
  });

  it("creates a work order via the API, refreshes the registry, and selects the new entry", async () => {
    const createdRecord = {
      work_order_code: "WO-1009",
      title: "Inspect coupling",
      asset_code: null,
      asset_type: null,
      description: "",
      priority: "MEDIUM",
      status: "OPEN",
      assigned_to: null,
      work_type: "CM",
      due_date: null,
      created_at: "2026-07-24",
    };

    getWorkOrders
      .mockResolvedValueOnce(WORK_ORDERS)
      .mockResolvedValueOnce([...WORK_ORDERS, createdRecord]);
    getWorkOrderAsset.mockResolvedValue({ success: true, area: "Unit 1" });
    getWorkOrderTimeline.mockResolvedValue([]);
    createWorkOrder.mockResolvedValue({ work_order_code: "WO-1009" });

    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1008");

    fireEvent.click(screen.getByRole("button", { name: "+ Create Work Order" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Inspect coupling" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Work Order" }));

    expect(screen.queryByRole("heading", { name: "Create Work Order" })).toBeNull();

    // UI-D2A -- identity header's <h1> is the work order's ID; title
    // (still the newly-created record's own real title) is subtitle text.
    expect(await screen.findByRole("heading", { name: "WO-1009" })).toBeTruthy();
    // UI-D2A.1 -- "Inspect coupling" now legitimately appears 3 times
    // (identity subtitle, desktop table row, mobile card row) instead of
    // 2 -- getAllByText().length, not toHaveLength, so this doesn't need
    // updating again the next time a representation is added/removed.
    expect(screen.getAllByText("Inspect coupling").length).toBeGreaterThan(0);
    expect((await screen.findByRole("status")).textContent).toContain("WO-1009 created.");

    expect(createWorkOrder).toHaveBeenCalledWith(
      expect.objectContaining({ work_order_code: "WO-1009", title: "Inspect coupling" })
    );
    expect(getWorkOrders).toHaveBeenCalledTimes(2);
  });

  it("shows an error and leaves the registry unchanged when create fails", async () => {
    loadWorkOrders();
    createWorkOrder.mockRejectedValue(new Error("work_order_code already exists"));

    render(<WorkOrder />);
    await within(await registryTable()).findByText("WO-1008");

    fireEvent.click(screen.getByRole("button", { name: "+ Create Work Order" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Inspect coupling" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Work Order" }));

    expect(await screen.findByText("Work order could not be created.")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Inspect coupling" })).toBeNull();
    expect(getWorkOrders).toHaveBeenCalledOnce();
  });
});
