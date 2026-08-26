import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PM from "./PM";
import {
  getPMSchedules, getPump, getCMReports, getPMOccurrences, getPMCMEvidence,
  updatePMSchedule, createPMSchedule,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- PM Schedule Edit UI and the PM
// no-schedule flow. A separate file from PM.test.jsx/PM.occurrence.test.jsx,
// same "one flow per file" convention those files already establish.
vi.mock("../../../api/ai5rClient", () => ({
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getCMReports: vi.fn(),
  getPMOccurrences: vi.fn(),
  getPMCMEvidence: vi.fn(),
  updatePMSchedule: vi.fn(),
  createPMSchedule: vi.fn(),
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
      <PM navContext={{ assetTag: "211-P-1A" }} />
    </AuthProvider>
  );
}

function renderWithWritePermission() {
  return renderWithSession(["maintenance.read", "maintenance.write"]);
}

function renderReadOnly() {
  return renderWithSession(["maintenance.read"], "PERTAMINA_ENGINEER");
}

const PM_SCHEDULE = {
  pm_schedule_code: "PM-2001",
  asset_code: "211-P-1A",
  procedure: "Lubrication & Vibration Check",
  frequency: "MONTHLY",
  trigger_type: "CALENDAR",
  interval_unit: "MONTH",
  effective_date: "2026-01-01",
  checklist: ["Check oil level"],
  next_due: "2026-09-01",
  assigned_to: "Sari Wulandari",
  status: "ACTIVE",
};

function loadPMSchedules(schedules = [PM_SCHEDULE]) {
  getPMSchedules.mockResolvedValue(schedules);
  getPump.mockResolvedValue({ tag_number: null, area: "Boiler House" });
  getCMReports.mockResolvedValue([]);
  getPMOccurrences.mockResolvedValue([]);
  getPMCMEvidence.mockResolvedValue([]);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("PM Schedule Edit UI (MWO-014C Gap A)", () => {
  it("shows an Edit Schedule action for an authorized (maintenance.write) user", async () => {
    loadPMSchedules();
    renderWithWritePermission();

    expect(await screen.findByRole("heading", { name: "Lubrication & Vibration Check" })).toBeTruthy();
    expect(screen.getByText("Edit Schedule")).toBeTruthy();
  });

  it("hides the Edit Schedule action for a read-only (no maintenance.write) session -- RBAC", async () => {
    loadPMSchedules();
    renderReadOnly();

    expect(await screen.findByRole("heading", { name: "Lubrication & Vibration Check" })).toBeTruthy();
    expect(screen.queryByText("Edit Schedule")).toBeNull();
  });

  it("prefills the edit form with the current canonical schedule values, and shows immutable identity read-only", async () => {
    loadPMSchedules();
    renderWithWritePermission();

    await screen.findByRole("heading", { name: "Lubrication & Vibration Check" });
    fireEvent.click(screen.getByText("Edit Schedule"));

    expect(screen.getByDisplayValue("PM-2001")).toBeDisabled();
    expect(screen.getByDisplayValue("211-P-1A")).toBeDisabled();
    expect(screen.getByDisplayValue("Lubrication & Vibration Check")).toBeTruthy();
    expect(screen.getByDisplayValue("Sari Wulandari")).toBeTruthy();
    expect(screen.getByDisplayValue("2026-09-01")).toBeTruthy();
  });

  it("calls the existing PATCH update endpoint with only the editable fields, never asset_code/pm_schedule_code, and never invents a value", async () => {
    loadPMSchedules();
    updatePMSchedule.mockResolvedValue({ data: { ...PM_SCHEDULE, procedure: "Updated Procedure" } });
    renderWithWritePermission();

    await screen.findByRole("heading", { name: "Lubrication & Vibration Check" });
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.change(screen.getByDisplayValue("Lubrication & Vibration Check"), {
      target: { value: "Updated Procedure" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(updatePMSchedule).toHaveBeenCalledTimes(1));
    const [code, payload] = updatePMSchedule.mock.calls[0];
    expect(code).toBe("PM-2001");
    expect(payload).toEqual({
      procedure: "Updated Procedure",
      frequency: "MONTHLY",
      trigger_type: "CALENDAR",
      interval_unit: "MONTH",
      effective_date: "2026-01-01",
      next_due: "2026-09-01",
      assigned_to: "Sari Wulandari",
      status: "ACTIVE",
    });
    expect(payload).not.toHaveProperty("asset_code");
    expect(payload).not.toHaveProperty("pm_schedule_code");
  });

  it("refreshes the displayed schedule from the server response after a successful update", async () => {
    loadPMSchedules();
    updatePMSchedule.mockResolvedValue({ data: { ...PM_SCHEDULE, procedure: "Updated Procedure" } });
    renderWithWritePermission();

    await screen.findByRole("heading", { name: "Lubrication & Vibration Check" });
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Updated Procedure" })).toBeTruthy());
  });

  it("surfaces a verbatim backend validation error and keeps the form open", async () => {
    loadPMSchedules();
    updatePMSchedule.mockRejectedValueOnce(new Error("next_due must be on or after effective_date"));
    renderWithWritePermission();

    await screen.findByRole("heading", { name: "Lubrication & Vibration Check" });
    fireEvent.click(screen.getByText("Edit Schedule"));
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    expect(await screen.findByTestId("edit-pm-schedule-error")).toHaveTextContent(
      "next_due must be on or after effective_date"
    );
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeTruthy();
  });
});

describe("PM no-schedule flow (MWO-014C Gap C)", () => {
  it('shows "No active PM Schedule is available for this pump." when the deep-linked pump has no matching schedule', async () => {
    loadPMSchedules([]);
    renderWithWritePermission();

    expect(await screen.findByText("No active PM Schedule is available for this pump.")).toBeTruthy();
  });

  it("offers Create PM Schedule to an authorized user, prefilled with the pump already being viewed", async () => {
    loadPMSchedules([]);
    renderWithWritePermission();

    await screen.findByText("No active PM Schedule is available for this pump.");
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(screen.getByDisplayValue("211-P-1A")).toBeTruthy();
  });

  it("does not offer Create PM Schedule to a read-only session", async () => {
    loadPMSchedules([]);
    renderReadOnly();

    await screen.findByText("No active PM Schedule is available for this pump.");
    expect(screen.queryByRole("button", { name: "Create PM Schedule" })).toBeNull();
  });

  it("AUTO_CREATE_PM_SCHEDULE=NO -- clicking Create PM Schedule only opens the form, it does not call the create API by itself", async () => {
    loadPMSchedules([]);
    renderWithWritePermission();

    await screen.findByText("No active PM Schedule is available for this pump.");
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(createPMSchedule).not.toHaveBeenCalled();
  });

  it("creating the schedule and recording a PM occurrence remain two separate user actions -- no occurrence form appears from the no-schedule empty state", async () => {
    loadPMSchedules([]);
    renderWithWritePermission();

    await screen.findByText("No active PM Schedule is available for this pump.");

    expect(screen.queryByText("+ Record PM Occurrence")).toBeNull();
    expect(screen.queryByTestId("pm-occurrence-form")).toBeNull();
  });
});
