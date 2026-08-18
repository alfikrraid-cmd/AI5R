import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PM from "./PM";
import { getPMSchedules, getPump, getCMReports, createPMOccurrence } from "../../../api/ai5rClient";

// MWO-LTSA-PM-CM-INTAKE-001 -- real PM Occurrence creation. A separate
// file from PM.test.jsx (same convention as Seal.identifiers.test.jsx),
// covering only the new "Record PM Occurrence" flow.
vi.mock("../../../api/ai5rClient", () => ({
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getCMReports: vi.fn(),
  createPMOccurrence: vi.fn(),
}));

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
    render(<PM />);
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
    render(<PM />);
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
    render(<PM />);
    await screen.findByText("PM-2001");
    fireEvent.click(screen.getByText("PM-2001"));

    fireEvent.click(await screen.findByText("+ Record PM Occurrence"));
    fireEvent.click(screen.getByText("Save Draft"));

    await screen.findByText(/PMOCC-NEW-2 recorded/);
    const call = createPMOccurrence.mock.calls[0][0];
    expect(call).not.toHaveProperty("createdBy");
    expect(call).not.toHaveProperty("updatedBy");
  });
});
