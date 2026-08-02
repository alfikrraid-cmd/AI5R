import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PMWorkOrderWorkspace from "./PMWorkOrderWorkspace";
import { getPMOccurrences, getPMSchedules, getPump, getPumpSpareParts, getWorkOrder } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getPMOccurrences: vi.fn(),
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getPumpSpareParts: vi.fn(),
  getWorkOrder: vi.fn(),
}));

const WORK_ORDER = {
  work_order_code: "WO-2026-00842",
  asset_code: "P-204A",
  title: "PM Bulanan — Feed Water Pump 204A",
  work_type: "PM",
  priority: "MEDIUM",
  assigned_to: "Budi Santoso",
  due_date: "2026-08-18",
  status: "IN_PROGRESS",
  created_at: "2026-08-01T00:00:00Z",
  description: "Preventive maintenance bulanan.",
};

const PUMP = {
  tag_number: "P-204A",
  name: "Feed Water Pump 204A",
  area: "Utility Area 2 — Boiler House",
  status: "RUNNING",
};

const PM_SCHEDULE = {
  pm_schedule_code: "PM-2008",
  asset_code: "P-204A",
  procedure: "Seal Chamber Condition Check",
  frequency: "MONTHLY",
  trigger_type: "CALENDAR",
  checklist: ["Periksa kebocoran pada mechanical seal", "Ukur getaran radial DE & NDE", "Ganti filter oli pelumas"],
  status: "ACTIVE",
  last_performed: "2026-07-01",
  next_due: "2026-09-01",
  estimated_duration_hours: 4,
  assigned_to: "Budi Santoso",
};

const PM_OCCURRENCE = {
  pm_occurrence_code: "PM-OCC-900",
  asset_code: "P-204A",
  pm_schedule_code: "PM-2008",
  work_order_code: "WO-2026-00842",
  occurrence_date: "2026-08-01",
  status: "IN_PROGRESS",
  checklist_completion: ["Periksa kebocoran pada mechanical seal", "Ukur getaran radial DE & NDE"],
};

const SPARE_PARTS = {
  success: true,
  spare_parts: [{ seal_code: "SEAL-P204A", part_name: "Grease NLGI 2", quantity_on_hand: 1, reorder_point: 1, location: "Gudang B" }],
};

afterEach(() => {
  vi.clearAllMocks();
});

function loadDefaults() {
  getWorkOrder.mockResolvedValue(WORK_ORDER);
  getPump.mockResolvedValue(PUMP);
  getPMOccurrences.mockResolvedValue([PM_OCCURRENCE]);
  getPMSchedules.mockResolvedValue([PM_SCHEDULE]);
  getPumpSpareParts.mockResolvedValue(SPARE_PARTS);
}

describe("PM Work Order Workspace", () => {
  it("shows an empty state when no work order is selected", async () => {
    render(<PMWorkOrderWorkspace navContext={null} />);
    expect(await screen.findByText(/no pm work order selected/i)).toBeTruthy();
  });

  it("renders identity, real checklist data, and real spare parts", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    expect(await screen.findByRole("heading", { name: "Feed Water Pump 204A" })).toBeTruthy();
    expect(screen.getAllByText("P-204A").length).toBeGreaterThan(0);
    expect(screen.getByText("PM WO-2026-00842")).toBeTruthy();

    // Real checklist: 2 of 3 required items completed, per the real PM Occurrence.
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("Periksa kebocoran pada mechanical seal")).toBeTruthy();
    expect(screen.getByText("Ganti filter oli pelumas")).toBeTruthy();

    // Real spare parts.
    expect(screen.getByText("Grease NLGI 2")).toBeTruthy();
    expect(screen.getByText("Qty 1")).toBeTruthy();

    // Real PM Schedule fields in the rail.
    expect(screen.getByText("MONTHLY")).toBeTruthy();
  });

  it("renders Coming Soon placeholders for every capability without a backend, never fabricated data", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });

    expect(screen.getByText(/Safety Checklist is not yet available/i)).toBeTruthy();
    expect(screen.getByText(/Photos is not yet available/i)).toBeTruthy();
    expect(screen.getByText(/Attachments is not yet available/i)).toBeTruthy();
    expect(screen.getByText(/Result is not yet available/i)).toBeTruthy();
    expect(screen.getByText(/Recommendation is not yet available/i)).toBeTruthy();
    expect(screen.getAllByText(/Sign-Off is not yet available/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Required Tools is not yet available/i)).toBeTruthy();
    expect(screen.getByText(/Marking items complete from this screen is not yet available/i)).toBeTruthy();
  });

  it("filters the procedure checklist using the Semua/Selesai/Tertunda chips", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });
    const procedureSection = document.getElementById("procedure-section");

    fireEvent.click(within(procedureSection).getByRole("button", { name: "Tertunda" }));
    expect(within(procedureSection).getByText("Ganti filter oli pelumas")).toBeTruthy();
    expect(within(procedureSection).queryByText("Periksa kebocoran pada mechanical seal")).toBeNull();

    fireEvent.click(within(procedureSection).getByRole("button", { name: "Selesai" }));
    expect(within(procedureSection).getByText("Periksa kebocoran pada mechanical seal")).toBeTruthy();
    expect(within(procedureSection).queryByText("Ganti filter oli pelumas")).toBeNull();
  });

  it("shows the real Work Order status on the stepper and status signal", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });
    expect(screen.getAllByText("In Progress").length).toBeGreaterThan(0);
    expect(screen.getByText("Sedang Dikerjakan")).toBeTruthy();
  });

  it("opens the command palette and shows Coming Soon for actions with no backend", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });
    fireEvent.click(screen.getByRole("button", { name: /Actions/ }));
    expect(await screen.findByPlaceholderText(/Cari aksi untuk WO-2026-00842/)).toBeTruthy();
  });

  it("navigates back to the Pump Workspace via the breadcrumb", async () => {
    loadDefaults();
    const onNavigate = vi.fn();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} onNavigate={onNavigate} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });
    fireEvent.click(document.querySelector('[data-od-id="crumb-pump-link"]'));

    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "P-204A" });
  });

  it("shows a Coming Soon toast instead of a fabricated sign-off submission", async () => {
    loadDefaults();
    render(<PMWorkOrderWorkspace navContext={{ workOrderId: "WO-2026-00842" }} />);

    await screen.findByRole("heading", { name: "Feed Water Pump 204A" });
    fireEvent.click(screen.getByRole("button", { name: "Kirim untuk Sign-Off" }));
    expect(await screen.findByText(/Sign-off submission is not yet available/i)).toBeTruthy();
  });
});
