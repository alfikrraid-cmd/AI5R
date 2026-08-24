import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoring from "./ConditionMonitoring";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, getPump, createConditionMonitoringReading,
  getPMCMEvidence,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/13 -- "+ Create Reading" is now
// gated on MAINTENANCE_WRITE (previously ungated, a Phase 13 violation
// this MWO fixed: Pertamina must never see a write control). Same
// AuthProvider-with-fake-client wrapping Seal.identifiers.test.jsx's own
// renderWithSession() established.
function renderWithSession(permissions, role = "TAP_ENGINEER", props) {
  const client = {
    getSession: () =>
      Promise.resolve({
        user: { name: "Test User" },
        organization: { displayName: "TAP" },
        role,
        permissions,
      }),
  };
  return render(
    <AuthProvider client={client}>
      <ConditionMonitoring {...props} />
    </AuthProvider>
  );
}

function renderWithWritePermission(props) {
  return renderWithSession(["maintenance.read", "condition.read", "maintenance.write"], "TAP_ENGINEER", props);
}

// MWO-LTSA-PM-CM-REVIEW-UI-001 -- ConditionMonitoringReadingDetailPanel
// now always renders the shared EvidenceAttachments widget once a reading
// is selected, so getPMCMEvidence must be mocked here too (the other new
// review-action API functions are exercised by
// ConditionMonitoring.review.test.jsx, a separate file, same convention
// as PM.occurrence.test.jsx alongside PM.test.jsx).
vi.mock("../../../api/ai5rClient", () => ({
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPump: vi.fn(),
  createConditionMonitoringReading: vi.fn(),
  getPMCMEvidence: vi.fn(),
  onUnauthorized: vi.fn(),
}));

const SCHEDULES = [
  {
    condition_monitoring_schedule_code: "CMON-SCHED-001",
    asset_code: "641-P-5",
    frequency: "WEEKLY",
    applicable_parameters: ["mechseal_temp", "mechanical_seal_leak"],
  },
  {
    condition_monitoring_schedule_code: "CMON-SCHED-002",
    asset_code: "418-P-1",
    frequency: "WEEKLY",
    applicable_parameters: [],
  },
];

const READINGS = [
  {
    condition_monitoring_reading_code: "CMON-READ-101",
    condition_monitoring_schedule_code: "CMON-SCHED-001",
    asset_code: "641-P-5",
    reading_date: "2026-07-12",
    mechseal_temp_de: 84,
    mechseal_temp_nde: 79,
    mechanical_seal_leak_de: true,
    mechanical_seal_leak_nde: false,
  },
  {
    condition_monitoring_reading_code: "CMON-READ-102",
    condition_monitoring_schedule_code: "CMON-SCHED-002",
    asset_code: "418-P-1",
    reading_date: "2026-07-13",
    mechseal_temp_de: 45,
    mechseal_temp_nde: 44,
    mechanical_seal_leak_de: false,
    mechanical_seal_leak_nde: false,
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

function loadDefaults() {
  getConditionMonitoringSchedules.mockResolvedValue(SCHEDULES);
  getConditionMonitoringReadings.mockResolvedValue(READINGS);
  getPump.mockResolvedValue({ tag_number: null, area: null });
  getPMCMEvidence.mockResolvedValue([]);
}

describe("Condition Monitoring workspace page", () => {
  it("renders the page header", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);

    expect(screen.getByRole("heading", { name: "Condition Monitoring" })).toBeTruthy();
    await screen.findByText("CMON-SCHED-001");
  });

  it("renders a loading state before the schedules API resolves", () => {
    getConditionMonitoringSchedules.mockReturnValue(new Promise(() => {}));
    getConditionMonitoringReadings.mockResolvedValue([]);
    render(<ConditionMonitoring />);

    expect(screen.getByText("Loading Condition Monitoring schedules...")).toBeTruthy();
  });

  it("renders schedule list API errors without fallback data", async () => {
    getConditionMonitoringSchedules.mockRejectedValue(new Error("API unavailable"));
    getConditionMonitoringReadings.mockResolvedValue([]);
    render(<ConditionMonitoring />);

    expect(await screen.findByText("Condition Monitoring schedules could not be loaded.")).toBeTruthy();
    expect(screen.queryByText("CMON-SCHED-001")).toBeNull();
  });

  it("renders every schedule from the canonical API in the list", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);

    for (const schedule of SCHEDULES) {
      expect(await screen.findByText(schedule.condition_monitoring_schedule_code)).toBeTruthy();
    }
    expect(getConditionMonitoringSchedules).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the schedule detail panel before any schedule is selected", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    expect(screen.getByText(/no condition monitoring schedule selected/i)).toBeTruthy();
  });

  it("shows the selected schedule's detail when a list row is clicked", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByText("CMON-SCHED-001"));

    expect(await screen.findByText("mechseal_temp")).toBeTruthy();
    expect(screen.getByText("mechanical_seal_leak")).toBeTruthy();
  });

  it("filters the schedule list by search text", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "418-P-1" } });

    expect(screen.getByText("CMON-SCHED-002")).toBeTruthy();
    expect(screen.queryByText("CMON-SCHED-001")).toBeNull();
  });

  it("switches to the Readings view and renders every reading", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));

    for (const reading of READINGS) {
      expect(await screen.findByText(reading.condition_monitoring_reading_code)).toBeTruthy();
    }
  });

  it("filters readings by leak status", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));
    await screen.findByText("CMON-READ-101");

    fireEvent.change(screen.getByRole("combobox", { name: /leak status/i }), { target: { value: "LEAK" } });

    expect(screen.getByText("CMON-READ-101")).toBeTruthy();
    expect(screen.queryByText("CMON-READ-102")).toBeNull();
  });

  it("shows reading detail when a reading row is clicked", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));
    await screen.findByText("CMON-READ-101");
    fireEvent.click(screen.getByText("CMON-READ-101"));

    expect(await screen.findByRole("heading", { name: "Reading Summary" })).toBeTruthy();
    expect(screen.getByText("Leak detected")).toBeTruthy();
  });

  it("opens the Create Reading modal when the header action is clicked", async () => {
    loadDefaults();
    renderWithWritePermission();
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(await screen.findByRole("button", { name: "+ Create Reading" }));

    expect(screen.getByRole("heading", { name: "Create Condition Monitoring Reading" })).toBeTruthy();
  });

  it("creates a new reading via the real API (MWO-LTSA-PM-CM-INTAKE-001), closes the modal, switches to Readings, and selects the new entry", async () => {
    loadDefaults();
    createConditionMonitoringReading.mockResolvedValue({
      data: {
        condition_monitoring_reading_code: "CMONR-NEW-1",
        condition_monitoring_schedule_code: "CMON-SCHED-001",
        asset_code: "641-P-5",
        reading_date: "2026-08-01",
        workflow_status: "DRAFT",
      },
    });
    renderWithWritePermission();
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(await screen.findByRole("button", { name: "+ Create Reading" }));
    fireEvent.change(screen.getByLabelText("Schedule"), { target: { value: "CMON-SCHED-001" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    expect(createConditionMonitoringReading).toHaveBeenCalledWith(
      expect.objectContaining({ conditionMonitoringScheduleCode: "CMON-SCHED-001", assetCode: "641-P-5" })
    );
    await screen.findByRole("heading", { name: "CMONR-NEW-1" });
    expect(screen.queryByRole("heading", { name: "Create Condition Monitoring Reading" })).toBeNull();
    expect(screen.getAllByText("CMONR-NEW-1").length).toBe(2);
    expect(screen.getByRole("status").textContent).toContain("CMONR-NEW-1 created (DRAFT).");
  });

  it("surfaces a verbatim backend error and keeps the modal open when create fails", async () => {
    loadDefaults();
    createConditionMonitoringReading.mockRejectedValueOnce(new Error("maintenance.write required"));
    renderWithWritePermission();
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(await screen.findByRole("button", { name: "+ Create Reading" }));
    fireEvent.change(screen.getByLabelText("Schedule"), { target: { value: "CMON-SCHED-001" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    expect(await screen.findByTestId("cmon-create-error")).toHaveProperty("textContent", "maintenance.write required");
    expect(screen.getByRole("heading", { name: "Create Condition Monitoring Reading" })).toBeTruthy();
  });

  it("navigates to Asset 360 when View Asset 360 is clicked from schedule detail", async () => {
    loadDefaults();
    const onNavigate = vi.fn();
    render(<ConditionMonitoring onNavigate={onNavigate} />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByText("CMON-SCHED-001"));
    fireEvent.click(await screen.findByRole("button", { name: "View Asset 360" }));

    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "641-P-5" });
  });

  it("navigates to Asset 360 when View Asset 360 is clicked from reading detail", async () => {
    loadDefaults();
    const onNavigate = vi.fn();
    render(<ConditionMonitoring onNavigate={onNavigate} />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));
    await screen.findByText("CMON-READ-101");
    fireEvent.click(screen.getByText("CMON-READ-101"));
    fireEvent.click(await screen.findByRole("button", { name: "View Asset 360" }));

    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "641-P-5" });
  });

  it("jumps from a reading's detail to its owning schedule within the same page", async () => {
    loadDefaults();
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));
    await screen.findByText("CMON-READ-101");
    fireEvent.click(screen.getByText("CMON-READ-101"));
    fireEvent.click(await screen.findByRole("button", { name: "CMON-SCHED-001" }));

    expect(await screen.findByText("mechseal_temp")).toBeTruthy();
  });

  it("pre-selects a schedule when navContext.selectId is provided (deep-link from Asset 360 Active Plans)", async () => {
    loadDefaults();
    render(<ConditionMonitoring navContext={{ selectId: "CMON-SCHED-002" }} />);

    expect(await screen.findByRole("heading", { name: "CMON-SCHED-002" })).toBeTruthy();
  });

  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001
  it("navContext.readingSelectId switches straight to the Readings view and opens the exact reading (Asset 360 Timeline deep-link)", async () => {
    getConditionMonitoringSchedules.mockResolvedValue(SCHEDULES);
    getConditionMonitoringReadings.mockResolvedValue([
      ...READINGS,
      {
        condition_monitoring_reading_code: "LTSA-CMONR-47FBA1F0416C8CB6",
        condition_monitoring_schedule_code: "UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx",
        asset_code: "220-P-4A",
        reading_date: "2026-06-24",
        mechseal_temp_de: 50,
        mechanical_seal_leak_de: true,
        finding: "Mechseal Bocor dari drain gland durasi 1/2 detik",
        source_workbook_name: "CM & PM Summary HOC JUNI.xlsx",
        source_sheet_name: "CM Measuring Report",
        source_row_number: 74,
      },
    ]);
    getPump.mockResolvedValue({ tag_number: null, area: null });
    getPMCMEvidence.mockResolvedValue([]);

    render(<ConditionMonitoring navContext={{ readingSelectId: "LTSA-CMONR-47FBA1F0416C8CB6" }} />);

    expect(await screen.findByRole("heading", { name: "LTSA-CMONR-47FBA1F0416C8CB6" })).toBeTruthy();
    expect(screen.getByText("Mechseal Bocor dari drain gland durasi 1/2 detik")).toBeTruthy();
  });

  it("resolves area per schedule and reading by reusing the existing Pump API", async () => {
    loadDefaults();
    getPump.mockImplementation((tag) =>
      Promise.resolve({ tag_number: tag, area: tag === "641-P-5" ? "SWS Unit" : null })
    );
    render(<ConditionMonitoring />);
    await screen.findByText("CMON-SCHED-001");

    expect(getPump).toHaveBeenCalledWith("641-P-5");
    expect(screen.getByText("SWS Unit")).toBeTruthy();
  });

  it("hides '+ Create Reading' for a Pertamina session (no maintenance.write) -- Phase 13", async () => {
    loadDefaults();
    renderWithSession(["maintenance.read", "condition.read"], "PERTAMINA_ENGINEER");
    await screen.findByText("CMON-SCHED-001");

    await waitFor(() => expect(screen.queryByRole("button", { name: "+ Create Reading" })).toBeNull());
  });
});
