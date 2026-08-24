import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PM from "./PM";
import {
  getPMSchedules, getPump, getCMReports, getPMOccurrences, createPMOccurrence, getPMCMEvidence,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-PM-CM-INTAKE-001 -- real PM Occurrence creation. A separate
// file from PM.test.jsx (same convention as Seal.identifiers.test.jsx),
// covering only the new "Record PM Occurrence" flow.
//
// MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- getPMCMEvidence added:
// selectedOccurrence is now resolved against the full pmOccurrences list
// (PM.jsx) rather than being implicitly gated behind selectedPM's own
// occurrencesForSelectedPM filter, so the newly-recorded occurrence in
// "creates a PM Occurrence..." below now reliably renders
// PMOccurrenceDetailPanel (and its embedded EvidenceAttachments widget)
// -- same mock every other file that renders that panel already carries.
vi.mock("../../../api/ai5rClient", () => ({
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getCMReports: vi.fn(),
  getPMOccurrences: vi.fn(),
  createPMOccurrence: vi.fn(),
  getPMCMEvidence: vi.fn(),
  onUnauthorized: vi.fn(),
}));

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/13 -- "+ Record PM Occurrence" is
// now gated on MAINTENANCE_WRITE (previously ungated, a Phase 13
// violation this MWO fixed: Pertamina must never see a write control).
// Same AuthProvider-with-fake-client wrapping Seal.identifiers.test.jsx's
// own renderWithSession() established.
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
      <PM />
    </AuthProvider>
  );
}

function renderWithWritePermission() {
  return renderWithSession(["maintenance.read", "maintenance.write"]);
}

const PM_SCHEDULES = [
  {
    pm_schedule_code: "PM-2001",
    asset_code: "211-P-1A",
    procedure: "Lubrication & Vibration Check",
    frequency: "MONTHLY",
    trigger_type: "CALENDAR",
    checklist: ["Check oil level"],
    status: "ACTIVE",
  },
];

function loadPMSchedules() {
  getPMSchedules.mockResolvedValue(PM_SCHEDULES);
  getPump.mockResolvedValue({ tag_number: null, area: "Boiler House" });
  getCMReports.mockResolvedValue([]);
  getPMOccurrences.mockResolvedValue([]);
  getPMCMEvidence.mockResolvedValue([]);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("PM workspace -- Record PM Occurrence (real persistence)", () => {
  it("shows no 'Record PM Occurrence' action until a schedule is selected", async () => {
    loadPMSchedules();
    render(<PM />);
    await screen.findByText("PM-2001");

    expect(screen.queryByText("+ Record PM Occurrence")).toBeNull();
  });

  it("creates a PM Occurrence via the real API once a schedule is selected", async () => {
    loadPMSchedules();
    createPMOccurrence.mockResolvedValue({ data: { pm_occurrence_code: "PMOCC-NEW-1", workflow_status: "DRAFT" } });
    renderWithWritePermission();
    await screen.findByText("PM-2001");
    fireEvent.click(screen.getByText("PM-2001"));

    fireEvent.click(await screen.findByText("+ Record PM Occurrence"));
    fireEvent.click(screen.getByLabelText("Flushing Line"));
    fireEvent.click(screen.getByText("Save Draft"));

    await screen.findByText(/PMOCC-NEW-1 recorded \(DRAFT\)/);
    expect(createPMOccurrence).toHaveBeenCalledWith(
      expect.objectContaining({
        pmScheduleCode: "PM-2001",
        assetCode: "211-P-1A",
        activities: expect.arrayContaining([
          expect.objectContaining({ code: "1", description: "Flushing Line", done: true }),
        ]),
      })
    );
    // the modal closes on success
    expect(screen.queryByTestId("pm-occurrence-form")).toBeNull();
  });

  it("surfaces a verbatim backend error and keeps the form open", async () => {
    loadPMSchedules();
    createPMOccurrence.mockRejectedValueOnce(new Error("maintenance.write required"));
    renderWithWritePermission();
    await screen.findByText("PM-2001");
    fireEvent.click(screen.getByText("PM-2001"));

    fireEvent.click(await screen.findByText("+ Record PM Occurrence"));
    fireEvent.click(screen.getByText("Save Draft"));

    expect(await screen.findByTestId("pm-occurrence-error")).toHaveProperty("textContent", "maintenance.write required");
    expect(screen.getByTestId("pm-occurrence-form")).toBeTruthy();
  });

  it("never sends created_by/updated_by from the client -- the request body has no such fields", async () => {
    loadPMSchedules();
    createPMOccurrence.mockResolvedValue({ data: { pm_occurrence_code: "PMOCC-NEW-2", workflow_status: "DRAFT" } });
    renderWithWritePermission();
    await screen.findByText("PM-2001");
    fireEvent.click(screen.getByText("PM-2001"));

    fireEvent.click(await screen.findByText("+ Record PM Occurrence"));
    fireEvent.click(screen.getByText("Save Draft"));

    await screen.findByText(/PMOCC-NEW-2 recorded/);
    const call = createPMOccurrence.mock.calls[0][0];
    expect(call).not.toHaveProperty("createdBy");
    expect(call).not.toHaveProperty("updatedBy");
  });

  it("hides '+ Record PM Occurrence' for a Pertamina session (no maintenance.write) -- Phase 13", async () => {
    loadPMSchedules();
    renderWithSession(["maintenance.read"], "PERTAMINA_ENGINEER");
    await screen.findByText("PM-2001");
    fireEvent.click(screen.getByText("PM-2001"));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Lubrication & Vibration Check" })).toBeTruthy());
    expect(screen.queryByText("+ Record PM Occurrence")).toBeNull();
  });
});
