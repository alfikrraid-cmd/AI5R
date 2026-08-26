import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HistoricalBatchReview from "./HistoricalBatchReview";
import {
  getPMOccurrences, getConditionMonitoringReadings,
  batchSubmitPMOccurrences, batchTechnicalReviewPMOccurrences,
  batchSubmitConditionMonitoringReadings, batchTechnicalReviewConditionMonitoringReadings,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019
vi.mock("../../../api/ai5rClient", () => ({
  getPMOccurrences: vi.fn(),
  getConditionMonitoringReadings: vi.fn(),
  batchSubmitPMOccurrences: vi.fn(),
  batchTechnicalReviewPMOccurrences: vi.fn(),
  batchSubmitConditionMonitoringReadings: vi.fn(),
  batchTechnicalReviewConditionMonitoringReadings: vi.fn(),
  onUnauthorized: vi.fn(),
}));

function renderWithRole(role, permissions) {
  const client = {
    getSession: () =>
      Promise.resolve({ user: { name: "Test User" }, organization: { displayName: "TAP" }, role, permissions }),
  };
  return render(
    <AuthProvider client={client}>
      <HistoricalBatchReview onNavigate={vi.fn()} />
    </AuthProvider>
  );
}

const PM_READY = {
  pm_occurrence_code: "PMOCC-READY-1", asset_code: "211-P-18A", occurrence_date: "2026-07-05",
  status: "DONE", activities: [{ code: "1", done: true }], workflow_status: "DRAFT",
  provenance: "HISTORICAL_IMPORT", source_reference: "document_field_extraction:DFE-1",
};
const PM_NEEDS_ATTENTION = {
  pm_occurrence_code: "PMOCC-NEEDS-1", asset_code: "211-P-18B", occurrence_date: "2026-07-06",
  status: "DONE", activities: [], workflow_status: "DRAFT",
  provenance: "HISTORICAL_IMPORT", source_reference: "document_field_extraction:DFE-2",
};
const PM_ALREADY_FINALIZED = {
  pm_occurrence_code: "PMOCC-JAN-1", asset_code: "211-P-19A", occurrence_date: "2026-01-05",
  status: "DONE", activities: [], workflow_status: "FINALIZED",
  provenance: "MANUAL", source_workbook_name: "Laporan PM, CM & Pemasangan Seal HCC JANUARI 2026.xlsx",
};

const CMON_READY = {
  condition_monitoring_reading_code: "CMONR-READY-1", asset_code: "220-P-4A", reading_date: "2026-07-01",
  mechseal_temp_de: 70, workflow_status: "DRAFT",
  provenance: "HISTORICAL_IMPORT", source_reference: "document_field_extraction:DFE-3",
};

afterEach(() => {
  vi.clearAllMocks();
});

function loadDefaults() {
  getPMOccurrences.mockResolvedValue([PM_READY, PM_NEEDS_ATTENTION, PM_ALREADY_FINALIZED]);
  getConditionMonitoringReadings.mockResolvedValue([CMON_READY]);
}

describe("HistoricalBatchReview", () => {
  it("renders the page and default PM counters derived from production data (J)", async () => {
    loadDefaults();
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);

    expect(screen.getByRole("heading", { name: "Historical Batch Review" })).toBeTruthy();
    const pmPanel = (await screen.findByText("PM", { selector: "strong" })).closest("div");
    expect(pmPanel.textContent).toContain("Ready for Review: 1");
    expect(pmPanel.textContent).toContain("Needs Attention: 1");
  });

  it("separates PM READY from NEEDS_ATTENTION under the default DRAFT filter (K)", async () => {
    loadDefaults();
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);

    await screen.findByText("PMOCC-READY-1");
    expect(screen.getByText("PMOCC-NEEDS-1")).toBeTruthy();
    // The already-FINALIZED January record is out of scope (workflow != DRAFT).
    expect(screen.queryByText("PMOCC-JAN-1")).toBeNull();
  });

  it("separates CMON READY from NEEDS_ATTENTION when the domain filter switches (L)", async () => {
    loadDefaults();
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);
    await screen.findByText("PMOCC-READY-1");

    fireEvent.change(screen.getByLabelText("Domain"), { target: { value: "CMON" } });

    expect(await screen.findByText("CMONR-READY-1")).toBeTruthy();
  });

  it("selection only ever includes currently visible rows -- switching domain clears it (M)", async () => {
    loadDefaults();
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);
    await screen.findByText("PMOCC-READY-1");

    fireEvent.click(screen.getByLabelText("Select PMOCC-READY-1"));
    expect(screen.getByText("1 selected")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Domain"), { target: { value: "CMON" } });
    expect(await screen.findByText("0 selected")).toBeTruthy();
  });

  it("shows the Batch Submit action only for a maintenance.write session (N)", async () => {
    loadDefaults();
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);
    await screen.findByText("PMOCC-READY-1");
    expect(screen.getByRole("button", { name: /Batch Submit/ })).toBeTruthy();
  });

  it("hides the Batch Submit action for a read-only session (N)", async () => {
    loadDefaults();
    renderWithRole("PERTAMINA_ENGINEER", ["maintenance.read", "condition.read"]);
    await screen.findByText("PMOCC-READY-1");
    expect(screen.queryByRole("button", { name: /Batch Submit/ })).toBeNull();
  });

  it("shows John Crane technical-review actions only for maintenance.technical_review (O)", async () => {
    loadDefaults();
    renderWithRole("JOHN_CRANE_ENGINEER", ["maintenance.read", "condition.read", "maintenance.technical_review"]);
    await screen.findByText("PMOCC-READY-1");
    expect(screen.getByRole("button", { name: /Batch Technically Approve/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Batch Submit/ })).toBeNull();
  });

  it("never sends a NEEDS_ATTENTION code that was not explicitly selected (P)", async () => {
    loadDefaults();
    batchSubmitPMOccurrences.mockResolvedValue({ succeeded: ["PMOCC-READY-1"], skipped: [], failed: [] });
    renderWithRole("TAP_ENGINEER", ["maintenance.read", "condition.read", "maintenance.write"]);
    await screen.findByText("PMOCC-READY-1");

    // Select only the READY row -- NEEDS_ATTENTION is deliberately left
    // unchecked, proving batch actions never silently sweep it in.
    fireEvent.click(screen.getByLabelText("Select PMOCC-READY-1"));
    fireEvent.click(screen.getByRole("button", { name: /Batch Submit/ }));

    await waitFor(() => expect(batchSubmitPMOccurrences).toHaveBeenCalledWith(["PMOCC-READY-1"]));
  });

  it("existing individual detail navigation still works via Open (Q)", async () => {
    loadDefaults();
    const onNavigate = vi.fn();
    const client = {
      getSession: () =>
        Promise.resolve({ user: { name: "Test User" }, organization: { displayName: "TAP" }, role: "TAP_ENGINEER", permissions: ["maintenance.read", "condition.read", "maintenance.write"] }),
    };
    render(
      <AuthProvider client={client}>
        <HistoricalBatchReview onNavigate={onNavigate} />
      </AuthProvider>
    );
    await screen.findByText("PMOCC-READY-1");

    const row = screen.getByText("PMOCC-READY-1").closest("tr");
    fireEvent.click(within(row).getByRole("button", { name: "Open" }));

    expect(onNavigate).toHaveBeenCalledWith("pm", { occurrenceSelectId: "PMOCC-READY-1" });
  });
});
