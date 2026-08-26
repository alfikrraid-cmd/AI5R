import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoring from "./ConditionMonitoring";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, getPump, getPMCMEvidence,
  updateConditionMonitoringSchedule,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- Condition Monitoring Schedule
// Edit UI. A separate file from ConditionMonitoring.test.jsx, same "one
// flow per file" convention PM.occurrence.test.jsx already establishes.
vi.mock("../../../api/ai5rClient", () => ({
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPump: vi.fn(),
  getPMCMEvidence: vi.fn(),
  updateConditionMonitoringSchedule: vi.fn(),
  onUnauthorized: vi.fn(),
}));

function renderWithSession(permissions, role = "TAP_ENGINEER") {
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
      <ConditionMonitoring />
    </AuthProvider>
  );
}

function renderWithWritePermission() {
  return renderWithSession(["maintenance.read", "condition.read", "maintenance.write"], "TAP_ENGINEER");
}

function renderReadOnly() {
  return renderWithSession(["maintenance.read", "condition.read"], "PERTAMINA_ENGINEER");
}

const SCHEDULE = {
  condition_monitoring_schedule_code: "CMON-SCHED-001",
  asset_code: "641-P-5",
  monitoring_type: "VIBRATION",
  measurement_point: "Drive End Bearing",
  frequency: "WEEKLY",
  interval_unit: "WEEK",
  effective_date: "2026-01-01",
  applicable_parameters: ["mechseal_temp", "mechanical_seal_leak"],
};

function loadDefaults(schedules = [SCHEDULE]) {
  getConditionMonitoringSchedules.mockResolvedValue(schedules);
  getConditionMonitoringReadings.mockResolvedValue([]);
  getPump.mockResolvedValue({ tag_number: null, area: null });
  getPMCMEvidence.mockResolvedValue([]);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("Condition Monitoring Schedule Edit UI (MWO-014C Gap B)", () => {
  it("shows an Edit Schedule action for an authorized (maintenance.write) user", async () => {
    loadDefaults();
    renderWithWritePermission();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));

    expect(screen.getByText("Edit Schedule")).toBeTruthy();
  });

  it("hides the Edit Schedule action for a read-only session -- RBAC", async () => {
    loadDefaults();
    renderReadOnly();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));

    expect(screen.queryByText("Edit Schedule")).toBeNull();
  });

  it("prefills the edit form with the current canonical schedule values, and shows immutable identity read-only", async () => {
    loadDefaults();
    renderWithWritePermission();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));
    fireEvent.click(screen.getByText("Edit Schedule"));

    expect(screen.getByDisplayValue("CMON-SCHED-001")).toBeDisabled();
    expect(screen.getByDisplayValue("641-P-5")).toBeDisabled();
    expect(screen.getByDisplayValue("VIBRATION")).toBeTruthy();
    expect(screen.getByDisplayValue("Drive End Bearing")).toBeTruthy();
    expect(screen.getByDisplayValue("WEEKLY")).toBeTruthy();
  });

  it("calls the existing PATCH update endpoint with only the editable fields, never asset_code/schedule code", async () => {
    loadDefaults();
    updateConditionMonitoringSchedule.mockResolvedValue({
      data: { ...SCHEDULE, monitoring_type: "TEMPERATURE" },
    });
    renderWithWritePermission();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.change(screen.getByDisplayValue("VIBRATION"), { target: { value: "TEMPERATURE" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(updateConditionMonitoringSchedule).toHaveBeenCalledTimes(1));
    const [code, payload] = updateConditionMonitoringSchedule.mock.calls[0];
    expect(code).toBe("CMON-SCHED-001");
    expect(payload).toEqual({
      monitoring_type: "TEMPERATURE",
      measurement_point: "Drive End Bearing",
      frequency: "WEEKLY",
      interval_unit: "WEEK",
      effective_date: "2026-01-01",
    });
    expect(payload).not.toHaveProperty("asset_code");
    expect(payload).not.toHaveProperty("condition_monitoring_schedule_code");
  });

  it("refreshes the displayed schedule from the server response after a successful update", async () => {
    loadDefaults();
    updateConditionMonitoringSchedule.mockResolvedValue({
      data: { ...SCHEDULE, frequency: "DAILY" },
    });
    renderWithWritePermission();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    // The Schedule Summary card (rendered outside the now-closed modal)
    // reflects the RETURNING response's frequency -- proves the update
    // reconciled real server data, not a locally-fabricated guess. "DAILY"
    // legitimately renders twice: the registry table row AND the detail
    // panel's Schedule Summary card.
    await waitFor(() => expect(screen.getAllByText("DAILY").length).toBeGreaterThan(0));
  });

  it("surfaces a verbatim backend validation error and keeps the form open", async () => {
    loadDefaults();
    updateConditionMonitoringSchedule.mockRejectedValueOnce(new Error("frequency is required"));
    renderWithWritePermission();

    await screen.findByText("CMON-SCHED-001");
    fireEvent.click(screen.getByText("CMON-SCHED-001"));
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    expect(await screen.findByTestId("edit-cmon-schedule-error")).toHaveTextContent("frequency is required");
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeTruthy();
  });
});

describe("Condition Monitoring no-schedule regression (MWO-014C) -- unchanged", () => {
  it("still shows the existing no-schedule message on the Readings view when no schedules exist", async () => {
    loadDefaults([]);
    renderWithWritePermission();

    fireEvent.click(screen.getByRole("tab", { name: "Readings" }));

    expect(await screen.findByText(/no active condition monitoring schedule is available for this pump/i)).toBeTruthy();
  });
});
