import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoring from "./ConditionMonitoring";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, getPump, getPMCMEvidence,
  createConditionMonitoringSchedule,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";
import { nextMonthFirstDay } from "../utils/pmMapping";

// "+ Create Schedule" is gated on MAINTENANCE_WRITE (ConditionMonitoring.jsx),
// same AuthProvider-with-fake-client wrapping ConditionMonitoring.scheduleEdit.test.jsx's
// own renderWithWritePermission() already establishes.
function renderWithWritePermission() {
  const client = {
    getSession: () =>
      Promise.resolve({
        user: { name: "Test User" },
        organization: { displayName: "TAP" },
        role: "TAP_ENGINEER",
        permissions: ["maintenance.read", "condition.read", "maintenance.write"],
      }),
  };
  return render(
    <AuthProvider client={client}>
      <ConditionMonitoring />
    </AuthProvider>
  );
}

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- covers the mission's own
// Phase 6 focused-test requirements that need a rendered
// <ConditionMonitoring /> (not just a pure function): default active-queue
// exclusion of COMPLETED/CANCELLED schedules (still reachable via the
// existing status filter), and next-month schedule creation. A separate
// file from ConditionMonitoring.test.jsx/ConditionMonitoring.scheduleEdit.test.jsx,
// same "one flow per file" convention those files already establish.
vi.mock("../../../api/ai5rClient", () => ({
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPump: vi.fn(),
  getPMCMEvidence: vi.fn(),
  createConditionMonitoringSchedule: vi.fn(),
  onUnauthorized: vi.fn(),
}));

const LIFECYCLE_SCHEDULES = [
  {
    condition_monitoring_schedule_code: "CMS-3001", asset_code: "641-P-5", frequency: "WEEKLY",
    applicable_parameters: [], status: "ACTIVE", next_due: "2020-06-15",
  },
  {
    condition_monitoring_schedule_code: "CMS-3002", asset_code: "641-P-6", frequency: "WEEKLY",
    applicable_parameters: [], status: "COMPLETED", next_due: "2020-01-01",
  },
  {
    condition_monitoring_schedule_code: "CMS-3003", asset_code: "641-P-7", frequency: "WEEKLY",
    applicable_parameters: [], status: "CANCELLED", next_due: "2020-01-01",
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

function loadLifecycleSchedules() {
  getConditionMonitoringSchedules.mockResolvedValue(LIFECYCLE_SCHEDULES);
  getConditionMonitoringReadings.mockResolvedValue([]);
  getPump.mockResolvedValue({ tag_number: null, area: null });
  getPMCMEvidence.mockResolvedValue([]);
}

describe("Condition Monitoring schedule lifecycle -- active work queue", () => {
  it("excludes COMPLETED and CANCELLED schedules from the default view", async () => {
    loadLifecycleSchedules();
    render(<ConditionMonitoring />);
    await screen.findByText("CMS-3001");

    expect(screen.queryByText("CMS-3002")).toBeNull();
    expect(screen.queryByText("CMS-3003")).toBeNull();
  });

  it("still shows a COMPLETED schedule when explicitly filtered for", async () => {
    loadLifecycleSchedules();
    render(<ConditionMonitoring />);
    await screen.findByText("CMS-3001");

    fireEvent.change(screen.getByRole("combobox", { name: /filter by status/i }), { target: { value: "COMPLETED" } });

    expect(screen.getByText("CMS-3002")).toBeTruthy();
    expect(screen.queryByText("CMS-3001")).toBeNull();
  });

  it("still shows a CANCELLED schedule when explicitly filtered for", async () => {
    loadLifecycleSchedules();
    render(<ConditionMonitoring />);
    await screen.findByText("CMS-3001");

    fireEvent.change(screen.getByRole("combobox", { name: /filter by status/i }), { target: { value: "CANCELLED" } });

    expect(screen.getByText("CMS-3003")).toBeTruthy();
    expect(screen.queryByText("CMS-3001")).toBeNull();
  });
});

describe("Condition Monitoring schedule lifecycle -- next-month creation default", () => {
  it("creates a schedule defaulting effective_date/next_due to the 1st of next calendar month", async () => {
    loadLifecycleSchedules();
    createConditionMonitoringSchedule.mockResolvedValue({
      data: {
        condition_monitoring_schedule_code: "CMS-3004", asset_code: "533-P-1", monitoring_type: "VIBRATION",
        frequency: "WEEKLY", applicable_parameters: [], status: "PLANNED",
      },
    });
    renderWithWritePermission();
    await screen.findByText("CMS-3001");

    fireEvent.click(screen.getByRole("button", { name: "+ Create Schedule" }));
    fireEvent.change(screen.getByLabelText("Schedule Code"), { target: { value: "CMS-3004" } });
    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Monitoring Type"), { target: { value: "VIBRATION" } });
    // Effective Date deliberately left untouched -- proving the DEFAULT
    // (not a user-entered value) is what reaches the API.
    fireEvent.click(screen.getByRole("button", { name: "Create Schedule" }));

    await waitFor(() => expect(createConditionMonitoringSchedule).toHaveBeenCalledOnce());
    const payload = createConditionMonitoringSchedule.mock.calls[0][0];
    const expected = nextMonthFirstDay();
    expect(payload.effective_date).toBe(expected);
    expect(payload.next_due).toBe(expected);
  });
});
