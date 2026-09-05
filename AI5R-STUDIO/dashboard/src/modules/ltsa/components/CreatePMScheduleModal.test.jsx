import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreatePMScheduleModal from "./CreatePMScheduleModal";
import { getPumps } from "../../../api/ai5rClient";

// AI5R-PHASE4E2 -- Schedule Code is system-generated (never a form field:
// OWNER DECISIONS 1-2), the hardcoded Checklist Template selector is
// removed entirely (OWNER DECISION 4, Section F), Procedure is replaced
// by an optional Notes field (OWNER DECISION 5), Trigger Type is derived
// automatically from Frequency and hidden (Section B), and Pump is now a
// searchable AssetSelector backed by the canonical pump master, never
// free text (Section C).
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
}));

const PUMPS = [
  { tag_number: "533-P-1", name: "Standby Transfer Pump" },
  { tag_number: "211-P-1A", name: "Boiler Feedwater Pump 1A" },
];

function loadPumps(pumps = PUMPS) {
  getPumps.mockResolvedValue(pumps);
}

describe("CreatePMScheduleModal", () => {
  it("renders nothing when closed", () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(screen.queryByText("Create PM Schedule")).toBeNull();
  });

  it("does not fetch pumps while closed", () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(getPumps).not.toHaveBeenCalled();
  });

  it("renders every form field when open, with no Schedule Code, Checklist Template, or Trigger Type input", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(await screen.findByLabelText("Pump *")).toBeTruthy();
    expect(screen.getByLabelText("Frequency *")).toBeTruthy();
    expect(screen.getByLabelText("Start Date *")).toBeTruthy();
    expect(screen.getByLabelText("Assigned Technician")).toBeTruthy();
    expect(screen.getByLabelText("Estimated Duration")).toBeTruthy();
    expect(screen.getByLabelText("Notes")).toBeTruthy();
    expect(screen.getByText("Planned Activities")).toBeTruthy();

    expect(screen.queryByLabelText("Schedule Code")).toBeNull();
    expect(screen.queryByLabelText("Procedure")).toBeNull();
    expect(screen.queryByLabelText("Checklist Template")).toBeNull();
    expect(screen.queryByLabelText("Trigger Type")).toBeNull();
    expect(screen.queryByLabelText("Equipment")).toBeNull();
  });

  it("offers exactly the four backend-supported frequency values, with human-friendly labels", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    const options = screen.getByLabelText("Frequency *").querySelectorAll("option");
    expect(Array.from(options).map((option) => option.value)).toEqual([
      "DAILY",
      "WEEKLY",
      "MONTHLY",
      "RUNTIME_BASED",
    ]);
    expect(Array.from(options).map((option) => option.textContent)).toEqual([
      "Daily",
      "Weekly",
      "Monthly",
      "Runtime-based",
    ]);
  });

  it("does not call onCreate and shows a field error when Pump is not selected", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);
    await screen.findByLabelText("Pump *");

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).not.toHaveBeenCalled();
    expect(await screen.findByText("Select a pump.")).toBeTruthy();
  });

  it("does not call onCreate and shows a field error when Start Date is cleared", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Start Date *"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).not.toHaveBeenCalled();
    expect(await screen.findByText("Select a start date.")).toBeTruthy();
  });

  it("rejects a negative Estimated Duration without calling onCreate", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Estimated Duration"), { target: { value: "-5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).not.toHaveBeenCalled();
    expect(await screen.findByText("Enter a duration of zero or more hours.")).toBeTruthy();
  });

  it("shows a readable pump-loading failure instead of a broken selector", async () => {
    getPumps.mockRejectedValue(new Error("Pumps API unavailable"));
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(await screen.findByText("Pumps API unavailable")).toBeTruthy();
    expect(screen.queryByLabelText("Pump *")).toBeNull();
  });

  it("shows the caller-supplied errorMessage (server-side failure) without ever rendering [object Object]", async () => {
    loadPumps();
    render(
      <CreatePMScheduleModal
        isOpen
        onClose={() => {}}
        onCreate={() => {}}
        errorMessage="Canonical pump not found"
      />
    );

    expect(await screen.findByText("Canonical pump not found")).toBeTruthy();
    expect(screen.queryByText(/object Object/i)).toBeNull();
  });

  it("derives Trigger Type from Frequency automatically (CALENDAR for MONTHLY, METER for RUNTIME_BASED)", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    expect(onCreate.mock.calls[0][0].triggerType).toBe("CALENDAR");

    onCreate.mockClear();
    fireEvent.change(screen.getByLabelText("Frequency *"), { target: { value: "RUNTIME_BASED" } });
    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    expect(onCreate.mock.calls[0][0].triggerType).toBe("METER");
  });

  it("calls onCreate with the resolved form values, and no planned activities when none are selected", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Frequency *"), { target: { value: "WEEKLY" } });
    fireEvent.change(screen.getByLabelText("Assigned Technician"), { target: { value: "Bagus Setiawan" } });
    fireEvent.change(screen.getByLabelText("Start Date *"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("Estimated Duration"), { target: { value: "2.5" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Bring spare gasket" } });

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    expect(onCreate).toHaveBeenCalledWith({
      equipmentTag: "533-P-1",
      frequency: "WEEKLY",
      triggerType: "CALENDAR",
      assignedTechnician: "Bagus Setiawan",
      startDate: "2026-08-01",
      estimatedDurationHours: 2.5,
      notes: "Bring spare gasket",
      plannedActivities: null,
    });
  });

  it("includes explicitly checked planned activities, with no `done` field or legacy numeric code, in the {family, variant, code} shape", async () => {
    loadPumps();
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });
    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));
    fireEvent.click(screen.getByLabelText("Reservoir"));

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    const payload = onCreate.mock.calls[0][0];
    expect(payload.plannedActivities).toEqual([
      { family: "Flushing Line", variant: "DE", code: "FLUSHING_LINE_DE" },
      { family: "Reservoir", variant: "GENERAL", code: "RESERVOIR" },
    ]);
    for (const entry of payload.plannedActivities) {
      expect(entry).not.toHaveProperty("done");
      expect(typeof entry.code).toBe("string");
      expect(entry.code).not.toMatch(/^\d+$/); // never a bare legacy numeric code
    }
  });

  it("leaves every planned activity checkbox unchecked initially", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    for (const checkbox of screen.getAllByRole("checkbox")) {
      expect(checkbox.checked).toBe(false);
    }
  });

  it("toggles General/DE/NDE for the same family independently", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));

    expect(screen.getByLabelText("Flushing Line DE Side").checked).toBe(true);
    expect(screen.getByLabelText("Flushing Line NDE Side").checked).toBe(false);
    expect(screen.getByLabelText("Flushing Line").checked).toBe(false);
  });

  it("offers Reservoir as General only (no DE/NDE variant exists)", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    expect(screen.getByLabelText("Reservoir")).toBeTruthy();
    expect(screen.queryByLabelText("Reservoir DE Side")).toBeNull();
    expect(screen.queryByLabelText("Reservoir NDE Side")).toBeNull();
  });

  it("keeps Cooler and Cooling Water Cooler distinct, and never displays WCH", async () => {
    loadPumps();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    expect(screen.getByLabelText("Cooler")).toBeTruthy();
    expect(screen.getByLabelText("Cooling Water Cooler")).toBeTruthy();
    expect(screen.queryByText(/WCH/)).toBeNull();
    expect(screen.queryByText(/Water-Cooled Heat Exchanger/i)).toBeNull();
  });

  it("calls onClose when Cancel is clicked", async () => {
    loadPumps();
    const onClose = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={onClose} onCreate={() => {}} />);
    await screen.findByLabelText("Pump *");

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
