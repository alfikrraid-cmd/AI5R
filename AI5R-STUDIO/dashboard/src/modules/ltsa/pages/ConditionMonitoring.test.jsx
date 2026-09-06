import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoring from "./ConditionMonitoring";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, getPump, createConditionMonitoringReading,
  createAdHocConditionMonitoringReading, createAdHocConditionMonitoringReadingsBulk, getPumps,
  parseConditionMonitoringExcel, downloadConditionMonitoringImportTemplate,
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
  getPumps: vi.fn(),
  createConditionMonitoringReading: vi.fn(),
  createAdHocConditionMonitoringReading: vi.fn(),
  createAdHocConditionMonitoringReadingsBulk: vi.fn(),
  parseConditionMonitoringExcel: vi.fn(),
  downloadConditionMonitoringImportTemplate: vi.fn(),
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
  getPumps.mockResolvedValue([{ tag_number: "641-P-5", name: "Pump 641-P-5" }]);
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

  // MWO-LTSA-CMON-ADHOC-ENTRY-001 -- the real gap this phase fixes: "+ Add
  // Reading" must work even with zero active schedules, unlike "+ Create
  // Reading" (still correctly hidden above zero schedules per the
  // unmodified schedules.length > 0 gate).
  describe("ad-hoc reading entry (MWO-LTSA-CMON-ADHOC-ENTRY-001)", () => {
    function loadWithNoSchedules() {
      getConditionMonitoringSchedules.mockResolvedValue([]);
      getConditionMonitoringReadings.mockResolvedValue([]);
      getPump.mockResolvedValue({ tag_number: null, area: null });
      getPumps.mockResolvedValue([{ tag_number: "641-P-5", name: "Pump 641-P-5" }]);
      getPMCMEvidence.mockResolvedValue([]);
    }

    it("shows '+ Add Reading' even when zero schedules exist, and '+ Create Reading' stays hidden", async () => {
      loadWithNoSchedules();
      renderWithWritePermission();
      await screen.findByRole("button", { name: "+ Add Reading" });

      expect(screen.queryByRole("button", { name: "+ Create Reading" })).toBeNull();
      expect(screen.getByRole("button", { name: "+ Add Reading" })).toBeTruthy();
    });

    it("hides '+ Add Reading' for a Pertamina session (no maintenance.write)", async () => {
      loadDefaults();
      renderWithSession(["maintenance.read", "condition.read"], "PERTAMINA_ENGINEER");
      await screen.findByText("CMON-SCHED-001");

      await waitFor(() => expect(screen.queryByRole("button", { name: "+ Add Reading" })).toBeNull());
    });

    it("opens the Add Reading modal without requiring any schedule", async () => {
      loadWithNoSchedules();
      renderWithWritePermission();
      await screen.findByRole("button", { name: "+ Add Reading" });

      fireEvent.click(screen.getByRole("button", { name: "+ Add Reading" }));

      expect(screen.getByRole("heading", { name: "Add Condition Monitoring Reading" })).toBeTruthy();
      expect(await screen.findByLabelText("Pump")).toBeTruthy();
      expect(screen.queryByLabelText("Schedule")).toBeNull();
    });

    it("creates an ad-hoc reading via the real API, with no schedule code sent, closes the modal, and selects the new entry", async () => {
      loadWithNoSchedules();
      createAdHocConditionMonitoringReading.mockResolvedValue({
        data: {
          condition_monitoring_reading_code: "CMONR-ADHOC-1",
          condition_monitoring_schedule_code: "UNSCHEDULED::MANUAL",
          asset_code: "641-P-5",
          reading_date: "2026-09-06",
          workflow_status: "DRAFT",
        },
      });
      renderWithWritePermission();
      await screen.findByRole("button", { name: "+ Add Reading" });

      fireEvent.click(screen.getByRole("button", { name: "+ Add Reading" }));
      fireEvent.change(await screen.findByLabelText("Pump"), { target: { value: "641-P-5" } });
      fireEvent.change(screen.getByLabelText("Reading Date"), { target: { value: "2026-09-06" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(createAdHocConditionMonitoringReading).toHaveBeenCalledWith(
        expect.objectContaining({ assetCode: "641-P-5", readingDate: "2026-09-06" })
      );
      const [callArgs] = createAdHocConditionMonitoringReading.mock.calls[0];
      expect(callArgs).not.toHaveProperty("conditionMonitoringScheduleCode");
      await screen.findByRole("heading", { name: "CMONR-ADHOC-1" });
      expect(screen.queryByRole("heading", { name: "Add Condition Monitoring Reading" })).toBeNull();
      expect(screen.getByRole("status").textContent).toContain("CMONR-ADHOC-1 created (DRAFT).");
    });

    it("all measurement fields start blank/not-recorded and DE/NDE toggle independently without mutating each other", async () => {
      loadWithNoSchedules();
      renderWithWritePermission();
      await screen.findByRole("button", { name: "+ Add Reading" });
      fireEvent.click(screen.getByRole("button", { name: "+ Add Reading" }));
      await screen.findByLabelText("Pump");

      expect(screen.getByLabelText("Mechanical Seal Temp DE")).toHaveProperty("value", "");
      expect(screen.getByLabelText("Mechanical Seal Temp NDE")).toHaveProperty("value", "");
      expect(screen.getByLabelText("Mechanical Seal Leak DE")).toHaveProperty("value", "");
      expect(screen.getByLabelText("Mechanical Seal Leak NDE")).toHaveProperty("value", "");

      fireEvent.change(screen.getByLabelText("Mechanical Seal Temp DE"), { target: { value: "75.2" } });
      expect(screen.getByLabelText("Mechanical Seal Temp DE")).toHaveProperty("value", "75.2");
      expect(screen.getByLabelText("Mechanical Seal Temp NDE")).toHaveProperty("value", "");

      fireEvent.change(screen.getByLabelText("Mechanical Seal Leak DE"), { target: { value: "false" } });
      expect(screen.getByLabelText("Mechanical Seal Leak DE")).toHaveProperty("value", "false");
      expect(screen.getByLabelText("Mechanical Seal Leak NDE")).toHaveProperty("value", "");
    });

    it("surfaces a verbatim backend error and keeps the Add Reading modal open when create fails", async () => {
      loadWithNoSchedules();
      createAdHocConditionMonitoringReading.mockRejectedValueOnce(new Error("Canonical pump not found"));
      renderWithWritePermission();
      await screen.findByRole("button", { name: "+ Add Reading" });

      fireEvent.click(screen.getByRole("button", { name: "+ Add Reading" }));
      fireEvent.change(await screen.findByLabelText("Pump"), { target: { value: "641-P-5" } });
      fireEvent.change(screen.getByLabelText("Reading Date"), { target: { value: "2026-09-06" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(await screen.findByTestId("cmon-create-error")).toHaveProperty("textContent", "Canonical pump not found");
      expect(screen.getByRole("heading", { name: "Add Condition Monitoring Reading" })).toBeTruthy();
    });
  });

  // MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- entry-point wiring only; the
  // editor's own exhaustive behavior (10-row UAT, row isolation, no
  // implicit propagation, atomic-flow contract) is covered directly and
  // more thoroughly by BulkCMONReadingEditor.test.jsx.
  describe("bulk reading entry (MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001)", () => {
    it("shows 'Bulk Reading' even with zero schedules, and opens the dedicated editor view", async () => {
      loadDefaults();
      getConditionMonitoringSchedules.mockResolvedValue([]);
      getConditionMonitoringReadings.mockResolvedValue([]);
      renderWithWritePermission();
      await screen.findByRole("button", { name: "Bulk Reading" });

      fireEvent.click(screen.getByRole("button", { name: "Bulk Reading" }));

      expect(screen.getByTestId("bulk-cmon-reading-editor")).toBeTruthy();
      expect(screen.queryByRole("heading", { name: "Condition Monitoring" })).toBeNull(); // dedicated full-width view, not a modal over the page
    });

    it("hides 'Bulk Reading' for a Pertamina session (no maintenance.write)", async () => {
      loadDefaults();
      renderWithSession(["maintenance.read", "condition.read"], "PERTAMINA_ENGINEER");
      await screen.findByText("CMON-SCHED-001");

      await waitFor(() => expect(screen.queryByRole("button", { name: "Bulk Reading" })).toBeNull());
    });

    it("closing the editor returns to the normal Condition Monitoring page", async () => {
      loadDefaults();
      renderWithWritePermission();
      await screen.findByRole("button", { name: "Bulk Reading" });
      fireEvent.click(screen.getByRole("button", { name: "Bulk Reading" }));
      await screen.findByTestId("bulk-cmon-reading-editor");

      fireEvent.click(screen.getByRole("button", { name: "Back to Condition Monitoring" }));

      expect(await screen.findByRole("heading", { name: "Condition Monitoring" })).toBeTruthy();
    });

    it("after a successful bulk create, closes the editor, shows the count, switches to Readings, and reloads the list", async () => {
      loadDefaults();
      getPumps.mockResolvedValue([{ tag_number: "641-P-5", name: "Pump 641-P-5" }]);
      createAdHocConditionMonitoringReadingsBulk.mockResolvedValue({
        data: [{ condition_monitoring_reading_code: "CMONR-BULK-1", asset_code: "641-P-5" }],
      });
      renderWithWritePermission();
      await screen.findByRole("button", { name: "Bulk Reading" });
      fireEvent.click(screen.getByRole("button", { name: "Bulk Reading" }));
      await screen.findByTestId("bulk-cmon-reading-editor");

      fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
      fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });
      fireEvent.change(screen.getByLabelText(/Reading Date for row/), { target: { value: "2026-09-06" } });
      fireEvent.click(screen.getByRole("button", { name: "Validate" }));
      await screen.findByTestId("bulk-cmon-validation-summary");
      fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));

      expect(await screen.findByRole("heading", { name: "Condition Monitoring" })).toBeTruthy(); // editor closed, back on the page
      expect(screen.getByRole("status").textContent).toContain("1 Condition Monitoring reading created.");
      await screen.findByText("CMON-READ-101"); // Readings view active and (re)loaded
      expect(getConditionMonitoringReadings).toHaveBeenCalledTimes(2); // initial load + post-bulk-create reload
    });
  });

  // MWO-LTSA-CMON-EXCEL-IMPORT-001 -- entry-point wiring only; the panel's
  // own exhaustive behavior is covered directly by CMONExcelImportPanel.test.jsx.
  describe("Excel import entry (MWO-LTSA-CMON-EXCEL-IMPORT-001)", () => {
    it("shows 'Import Excel' even with zero schedules, and opens the dedicated import panel", async () => {
      loadDefaults();
      getConditionMonitoringSchedules.mockResolvedValue([]);
      getConditionMonitoringReadings.mockResolvedValue([]);
      renderWithWritePermission();
      await screen.findByRole("button", { name: "Import Excel" });

      fireEvent.click(screen.getByRole("button", { name: "Import Excel" }));

      expect(screen.getByTestId("cmon-excel-import-panel")).toBeTruthy();
      expect(screen.queryByRole("heading", { name: "Condition Monitoring" })).toBeNull();
    });

    it("hides 'Import Excel' for a Pertamina session (no maintenance.write)", async () => {
      loadDefaults();
      renderWithSession(["maintenance.read", "condition.read"], "PERTAMINA_ENGINEER");
      await screen.findByText("CMON-SCHED-001");

      await waitFor(() => expect(screen.queryByRole("button", { name: "Import Excel" })).toBeNull());
    });

    it("Review in Bulk Editor from the import panel transitions directly into the Bulk Editor with the parsed rows seeded", async () => {
      loadDefaults();
      getPumps.mockResolvedValue([{ tag_number: "641-P-5", name: "Pump 641-P-5" }]);
      parseConditionMonitoringExcel.mockResolvedValue({
        data: {
          headers: ["Pump Tag *", "Reading Date *", "Mechanical Seal Temp DE"],
          rows: [["641-P-5", "2026-09-06", "75.2"]],
        },
      });
      renderWithWritePermission();
      await screen.findByRole("button", { name: "Import Excel" });
      fireEvent.click(screen.getByRole("button", { name: "Import Excel" }));
      await screen.findByTestId("cmon-excel-import-panel");

      fireEvent.change(screen.getByLabelText("Upload Condition Monitoring Excel file"), {
        target: { files: [new File(["dummy"], "readings.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" })] },
      });
      fireEvent.click(screen.getByRole("button", { name: "Parse File" }));
      await screen.findByTestId("cmon-excel-import-preview");
      fireEvent.click(screen.getByRole("button", { name: "Review in Bulk Editor" }));

      expect(await screen.findByTestId("bulk-cmon-reading-editor")).toBeTruthy();
      expect(screen.queryByTestId("cmon-excel-import-panel")).toBeNull();
      const pumpSelect = screen.getByLabelText("Pump");
      expect(pumpSelect.value).toBe("641-P-5"); // seeded from the imported row, not re-entered manually
    });
  });
});
