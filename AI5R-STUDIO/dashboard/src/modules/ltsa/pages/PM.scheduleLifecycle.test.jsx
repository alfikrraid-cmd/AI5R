import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PM from "./PM";
import { getPMSchedules, getPump, getCMReports, getPMOccurrences, getPMCMEvidence, createPMSchedule } from "../../../api/ai5rClient";
import { nextMonthFirstDay } from "../utils/pmMapping";

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- covers the mission's own
// Phase 3 focused-test requirements that need a rendered <PM /> (not just
// a pure function): default active-queue exclusion of COMPLETED/
// CANCELLED (still reachable via the existing status filter), and
// next-month schedule creation. A separate file from PM.test.jsx/
// PM.scheduleEdit.test.jsx, same "one flow per file" convention those
// files already establish.
vi.mock("../../../api/ai5rClient", () => ({
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getCMReports: vi.fn(),
  getPMOccurrences: vi.fn(),
  getPMCMEvidence: vi.fn(),
  createPMSchedule: vi.fn(),
}));

const LIFECYCLE_SCHEDULES = [
  {
    pm_schedule_code: "PM-3001", asset_code: "211-P-1A", procedure: "Active Job", frequency: "MONTHLY",
    trigger_type: "CALENDAR", checklist: [], next_due: "2020-06-15", assigned_to: "Tech A",
    estimated_duration_hours: 1, status: "ACTIVE",
  },
  {
    pm_schedule_code: "PM-3002", asset_code: "211-P-1B", procedure: "Completed Job", frequency: "MONTHLY",
    trigger_type: "CALENDAR", checklist: [], next_due: "2020-01-01", assigned_to: "Tech B",
    estimated_duration_hours: 1, status: "COMPLETED",
  },
  {
    pm_schedule_code: "PM-3003", asset_code: "211-P-1C", procedure: "Cancelled Job", frequency: "MONTHLY",
    trigger_type: "CALENDAR", checklist: [], next_due: "2020-01-01", assigned_to: "Tech C",
    estimated_duration_hours: 1, status: "CANCELLED",
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

function loadLifecycleSchedules() {
  getPMSchedules.mockResolvedValue(LIFECYCLE_SCHEDULES);
  getPump.mockResolvedValue({ tag_number: null, area: "Boiler House" });
  getCMReports.mockResolvedValue([]);
  getPMOccurrences.mockResolvedValue([]);
}

describe("PM schedule lifecycle -- active work queue", () => {
  it("excludes COMPLETED and CANCELLED schedules from the default view", async () => {
    loadLifecycleSchedules();
    render(<PM />);
    await screen.findByText("PM-3001");

    expect(screen.queryByText("PM-3002")).toBeNull();
    expect(screen.queryByText("PM-3003")).toBeNull();
  });

  it("still shows a COMPLETED schedule when explicitly filtered for", async () => {
    loadLifecycleSchedules();
    render(<PM />);
    await screen.findByText("PM-3001");

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "COMPLETED" } });

    expect(screen.getByText("PM-3002")).toBeTruthy();
    expect(screen.queryByText("PM-3001")).toBeNull();
  });

  it("still shows a CANCELLED schedule when explicitly filtered for", async () => {
    loadLifecycleSchedules();
    render(<PM />);
    await screen.findByText("PM-3001");

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CANCELLED" } });

    expect(screen.getByText("PM-3003")).toBeTruthy();
    expect(screen.queryByText("PM-3001")).toBeNull();
  });
});

describe("PM schedule lifecycle -- next-month creation default", () => {
  it("creates a schedule defaulting next_due/effective_date to the 1st of next calendar month", async () => {
    loadLifecycleSchedules();
    createPMSchedule.mockResolvedValue({
      data: {
        pm_schedule_code: "PM-3004", asset_code: "533-P-1", procedure: "Standard Lubrication",
        frequency: "MONTHLY", trigger_type: "CALENDAR", status: "ACTIVE", checklist: [],
      },
    });
    render(<PM />);
    await screen.findByText("PM-3001");

    fireEvent.click(screen.getByRole("button", { name: "+ Create PM Schedule" }));
    fireEvent.change(screen.getByLabelText("Schedule Code"), { target: { value: "PM-3004" } });
    fireEvent.change(screen.getByLabelText("Procedure"), { target: { value: "Standard Lubrication" } });
    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    // Start Date deliberately left untouched -- proving the DEFAULT (not a
    // user-entered value) is what reaches the API.
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    await waitFor(() => expect(createPMSchedule).toHaveBeenCalledOnce());
    const payload = createPMSchedule.mock.calls[0][0];
    const expected = nextMonthFirstDay();
    expect(payload.next_due).toBe(expected);
    expect(payload.effective_date).toBe(expected);
  });
});
