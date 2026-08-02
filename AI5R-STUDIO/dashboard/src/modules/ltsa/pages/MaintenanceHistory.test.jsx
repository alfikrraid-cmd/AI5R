import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MaintenanceHistory from "./MaintenanceHistory";
import {
  getCMReports,
  getConditionMonitoringReadings,
  getConditionMonitoringSchedules,
  getMaintenanceHistory,
  getPMOccurrences,
  getPMSchedules,
  getPumpConditionMonitoringFlag,
  getPumpLastCM,
  getPumpLastPM,
  getPumpOpenWorkOrders,
  getPumpSpareParts,
  getPumps,
  getWorkOrders,
} from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getCMReports: vi.fn(),
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getMaintenanceHistory: vi.fn(),
  getPMOccurrences: vi.fn(),
  getPMSchedules: vi.fn(),
  getPumpConditionMonitoringFlag: vi.fn(),
  getPumpLastCM: vi.fn(),
  getPumpLastPM: vi.fn(),
  getPumpOpenWorkOrders: vi.fn(),
  getPumpSpareParts: vi.fn(),
  getPumps: vi.fn(),
  getWorkOrders: vi.fn(),
}));

const PUMPS = [
  {
    tag_number: "641-P-5",
    name: "Sour Water Stripper Bottoms Pump",
    area: "SWS Unit",
    status: "FAULT",
    criticality: "HIGH",
    pump_type: "Centrifugal (API 610 OH2)",
    api_plan: "11/61",
    seal_type: "John Crane 502",
  },
  {
    tag_number: "211-P-1A",
    name: "Boiler Feedwater Pump 1A",
    area: "Boiler House",
    status: "RUNNING",
    criticality: "HIGH",
    pump_type: "Centrifugal (API 610)",
    api_plan: "11/61",
    seal_type: "John Crane Type 21",
  },
];

const WORK_ORDERS = [
  {
    work_order_code: "WO-1001",
    asset_code: "641-P-5",
    title: "Seal replacement — repeat failures",
    description: "Third seal failure in 90 days.",
    status: "OPEN",
    work_type: "CM",
    assigned_to: "Dedi Kurniawan",
    due_date: "2026-07-21",
    created_at: "2026-07-18T00:00:00Z",
  },
];

const MAINTENANCE_HISTORY = [];

const CM_REPORTS = [
  {
    cm_report_code: "CM-3001",
    asset_code: "641-P-5",
    failure_category: "SEAL_FAILURE",
    severity: "CRITICAL",
    priority: "CRITICAL",
    failure_description: "Third mechanical seal failure in 90 days.",
    status: "IN_PROGRESS",
    assigned_to: "Dedi Kurniawan",
    created_at: "2026-07-18T00:00:00Z",
    work_order_code: "WO-1001",
    downtime_hours: 6.5,
  },
  {
    cm_report_code: "CM-3002",
    asset_code: "641-P-5",
    failure_category: "MINOR",
    severity: "LOW",
    priority: "LOW",
    failure_description: "Minor adjustment, no downtime.",
    status: "CLOSED",
    assigned_to: "Dedi Kurniawan",
    created_at: "2026-06-01T00:00:00Z",
    work_order_code: null,
    downtime_hours: 0,
  },
];

const PM_OCCURRENCES = [
  {
    pm_occurrence_code: "PM-OCC-101",
    asset_code: "641-P-5",
    pm_schedule_code: "PM-2008",
    occurrence_date: "2025-12-10T00:00:00Z",
    status: "DONE",
    checklist_completion: ["Inspect seal chamber for leakage"],
    work_order_code: null,
  },
];

const CONDITION_MONITORING_READINGS = [];
const PM_SCHEDULES = [];
const CONDITION_MONITORING_SCHEDULES = [];

const SPARE_PARTS = {
  success: true,
  spare_parts: [
    { seal_code: "SEAL-641-P-5", part_name: "Mechanical Seal — Type 5610", quantity_on_hand: 2, reorder_point: 1, location: "Gudang B · Rak 12" },
    { seal_code: "SEAL-641-P-5", part_name: "Bearing 6309-2RS", quantity_on_hand: 0, reorder_point: 2, location: "Gudang B · Rak 07" },
  ],
};

afterEach(() => {
  vi.clearAllMocks();
});

function loadDefaults() {
  getPumps.mockResolvedValue(PUMPS);
  getWorkOrders.mockResolvedValue(WORK_ORDERS);
  getMaintenanceHistory.mockResolvedValue(MAINTENANCE_HISTORY);
  getCMReports.mockResolvedValue(CM_REPORTS);
  getPMOccurrences.mockResolvedValue(PM_OCCURRENCES);
  getConditionMonitoringReadings.mockResolvedValue(CONDITION_MONITORING_READINGS);
  getPMSchedules.mockResolvedValue(PM_SCHEDULES);
  getConditionMonitoringSchedules.mockResolvedValue(CONDITION_MONITORING_SCHEDULES);
  getPumpLastPM.mockResolvedValue({ success: true, tag_number: "641-P-5", last_pm: { performed_at: "2025-12-10" } });
  getPumpLastCM.mockResolvedValue({ success: true, tag_number: "641-P-5", last_cm: { cm_report_code: "CM-3001" } });
  getPumpConditionMonitoringFlag.mockResolvedValue({ success: true, tag_number: "641-P-5", flagged: false });
  getPumpOpenWorkOrders.mockResolvedValue({ success: true, tag_number: "641-P-5", openWO: 1, data: WORK_ORDERS });
  getPumpSpareParts.mockResolvedValue(SPARE_PARTS);
}

function selectAsset(tag) {
  fireEvent.change(screen.getByLabelText("Select Asset"), { target: { value: tag } });
}

describe("Pump Workspace (ITD-Frontend Phase 1)", () => {
  it("shows the asset picker before any pump is selected", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    expect(screen.getByText(/no pump selected/i)).toBeTruthy();
  });

  it("renders the approved chrome bar, identity, and inspector rail once a pump is selected", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");

    expect(await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" })).toBeTruthy();
    expect(screen.getAllByText("641-P-5").length).toBeGreaterThan(0);
    expect(screen.getByText("SWS Unit")).toBeTruthy();
    expect(screen.getByText("Fault")).toBeTruthy();

    expect(screen.getByRole("heading", { name: "Mechanical Seal" })).toBeTruthy();
    expect(screen.getByText("John Crane 502")).toBeTruthy();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);

    expect(screen.getByRole("heading", { name: "Related Spare Parts" })).toBeTruthy();
    expect(screen.getByText("Mechanical Seal — Type 5610")).toBeTruthy();
    expect(screen.getByText("Qty 2")).toBeTruthy();
    expect(screen.getByText("Stok Habis")).toBeTruthy();

    expect(screen.getByRole("heading", { name: "Drawing" })).toBeTruthy();
  });

  it("renders the AI Assessment panel as an explicit Coming Soon placeholder, not fabricated data", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");

    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    expect(screen.getByText("Reliability Assessment")).toBeTruthy();
    expect(screen.getAllByText(/coming soon/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/AI Assessment is not yet available/i)).toBeTruthy();
  });

  it("splits real CM Report events into cm vs breakdown tiers using the real downtime_hours field", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    const timelineSection = screen.getByText("History").closest("section");

    expect(within(timelineSection).getByText("BREAKDOWN")).toBeTruthy();
    expect(within(timelineSection).getByText(/Third mechanical seal failure/)).toBeTruthy();
    expect(within(timelineSection).getByText(/Minor adjustment, no downtime/)).toBeTruthy();
  });

  it("filters the timeline using the approved Semua/PM/CM/Breakdown chips", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    const timelineSection = (await screen.findByText("History")).closest("section");

    fireEvent.click(within(timelineSection).getByRole("button", { name: "PM" }));
    expect(within(timelineSection).getByText(/PM Occurrence/)).toBeTruthy();
    expect(within(timelineSection).queryByText("Third mechanical seal failure in 90 days.")).toBeNull();

    fireEvent.click(within(timelineSection).getByRole("button", { name: "Semua" }));
    expect(within(timelineSection).getByText(/PM Occurrence/)).toBeTruthy();
  });

  it("opens the command palette via the Actions trigger and via Cmd+K", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });

    fireEvent.click(screen.getByRole("button", { name: /Actions/ }));
    expect(await screen.findByPlaceholderText(/Cari aksi untuk/)).toBeTruthy();

    fireEvent.keyDown(screen.getByPlaceholderText(/Cari aksi untuk/), { key: "Escape" });
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(await screen.findByPlaceholderText(/Cari aksi untuk/)).toBeTruthy();
  });

  it("shows a Coming Soon toast instead of fabricating a scheduled inspection or a submitted CM", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });

    fireEvent.click(screen.getByRole("button", { name: /Jadwalkan Inspeksi/ }));
    expect(await screen.findByText(/Jadwalkan Inspeksi is not yet available/i)).toBeTruthy();
  });

  it("opens the CM drawer and shows a Coming Soon placeholder instead of a fabricated submission", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });

    fireEvent.click(screen.getByRole("button", { name: /Ajukan CM manual/ }));
    expect(await screen.findByRole("heading", { name: "Ajukan Corrective Maintenance" })).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText(/Getaran radial meningkat/), { target: { value: "Test note" } });
    fireEvent.click(screen.getByRole("button", { name: "Kirim Pengajuan" }));
    expect(await screen.findByText(/Ajukan CM is not yet available/i)).toBeTruthy();
  });

  it("toggles the theme without affecting the rest of the app", async () => {
    loadDefaults();
    render(<MaintenanceHistory />);

    await screen.findByLabelText("Select Asset");
    selectAsset("641-P-5");
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });

    const root = document.querySelector(".pump-workspace-root");
    expect(root.getAttribute("data-theme")).toBe("light");

    fireEvent.click(screen.getByLabelText("Toggle theme"));
    expect(root.getAttribute("data-theme")).toBe("dark");
  });

  it("pre-selects the asset when navContext.assetTag is provided (deep-link entry point)", async () => {
    loadDefaults();
    render(<MaintenanceHistory navContext={{ assetTag: "641-P-5" }} />);

    expect(await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" })).toBeTruthy();
  });
});
