import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoring from "./ConditionMonitoring";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, getPump, getPMCMEvidence,
  deleteConditionMonitoringReading,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// LTSA_CONDITION_MONITORING_SAFE_DRAFT_DELETE_R2 -- reading Soft Delete is
// gated on maintenance.write (never a role name) and, after a successful
// delete, the list is re-fetched so the soft-deleted reading disappears.
// Separate file, same "one flow per file" convention as
// ConditionMonitoring.scheduleLifecycle.test.jsx.
vi.mock("../../../api/ai5rClient", () => ({
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPump: vi.fn(),
  getPMCMEvidence: vi.fn(),
  deleteConditionMonitoringReading: vi.fn(),
  onUnauthorized: vi.fn(),
}));

function renderWithSession(permissions, role) {
  const client = {
    getSession: () =>
      Promise.resolve({ user: { name: "Test User" }, organization: { displayName: "TAP" }, role, permissions }),
  };
  return render(
    <AuthProvider client={client}>
      <ConditionMonitoring />
    </AuthProvider>
  );
}

const WRITE = ["maintenance.read", "condition.read", "maintenance.write"];

const DRAFT = {
  condition_monitoring_reading_code: "CMONR-4B33E52CA2B5",
  condition_monitoring_schedule_code: "UNSCHEDULED::MANUAL",
  asset_code: "211-P-13AR",
  reading_date: "2026-08-29",
  workflow_status: "DRAFT",
  provenance: "MANUAL",
};
const SUBMITTED = {
  ...DRAFT,
  condition_monitoring_reading_code: "CMONR-SUBMITTED",
  workflow_status: "SUBMITTED",
};

beforeEach(() => {
  getConditionMonitoringSchedules.mockResolvedValue([]);
  getConditionMonitoringReadings.mockResolvedValue([DRAFT, SUBMITTED]);
  getPump.mockResolvedValue({ tag_number: null, area: null });
  getPMCMEvidence.mockResolvedValue([]);
  vi.spyOn(window, "prompt").mockReturnValue("Entered by mistake");
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

async function selectReading(code) {
  const table = await screen.findByRole("table");
  fireEvent.click(await within(table).findByText(code));
  await screen.findByRole("heading", { name: "Reading Detail" });
}

describe("Condition Monitoring reading safe DRAFT delete", () => {
  it("a non-SUPERUSER maintenance.write user deletes a DRAFT; list refreshes and the record disappears", async () => {
    deleteConditionMonitoringReading.mockResolvedValue({ data: { ...DRAFT, deleted_at: "2026-09-27T10:00:00Z" } });
    renderWithSession(WRITE, "TAP_ENGINEER");
    await selectReading("CMONR-4B33E52CA2B5");

    getConditionMonitoringReadings.mockResolvedValue([SUBMITTED]);
    fireEvent.click(await screen.findByRole("button", { name: "Soft Delete" }));

    await waitFor(() =>
      expect(deleteConditionMonitoringReading).toHaveBeenCalledWith("CMONR-4B33E52CA2B5", "Entered by mistake")
    );
    expect(await screen.findByText("Condition Monitoring reading CMONR-4B33E52CA2B5 soft-deleted.")).toBeTruthy();
    await waitFor(() => expect(getConditionMonitoringReadings).toHaveBeenCalledTimes(2));
    const table = await screen.findByRole("table");
    await waitFor(() => expect(within(table).queryByText("CMONR-4B33E52CA2B5")).toBeNull());
    expect(within(table).getByText("CMONR-SUBMITTED")).toBeTruthy();
    expect(screen.getByText("No Condition Monitoring reading selected")).toBeTruthy();
  });

  it("hides Soft Delete for a session without maintenance.write", async () => {
    renderWithSession(["maintenance.read", "condition.read", "maintenance.technical_review"], "JOHN_CRANE_ENGINEER");
    await selectReading("CMONR-4B33E52CA2B5");
    expect(screen.queryByRole("button", { name: "Soft Delete" })).toBeNull();
  });

  it("hides Soft Delete on a SUBMITTED reading even for maintenance.write", async () => {
    renderWithSession(WRITE, "TAP_ADMIN");
    await selectReading("CMONR-SUBMITTED");
    expect(screen.queryByRole("button", { name: "Soft Delete" })).toBeNull();
  });

  it("a 409 from the API is shown and the reading stays listed and selected", async () => {
    deleteConditionMonitoringReading.mockRejectedValue(
      new Error("Only a DRAFT Condition Monitoring reading that is not a historical import can be deleted")
    );
    renderWithSession(WRITE, "TAP_ENGINEER");
    await selectReading("CMONR-4B33E52CA2B5");

    fireEvent.click(await screen.findByRole("button", { name: "Soft Delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Only a DRAFT Condition Monitoring reading that is not a historical import can be deleted"
    );
    expect(getConditionMonitoringReadings).toHaveBeenCalledTimes(1);
    expect(within(await screen.findByRole("table")).getByText("CMONR-4B33E52CA2B5")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Reading Detail" })).toBeTruthy();
  });
});
