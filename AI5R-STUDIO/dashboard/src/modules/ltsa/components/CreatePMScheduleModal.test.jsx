import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreatePMScheduleModal from "./CreatePMScheduleModal";

// AI5R-PHASE4E1 -- Schedule Code is now system-generated (never a form
// field: OWNER DECISIONS 1-2), the hardcoded Checklist Template selector
// is removed entirely (OWNER DECISION 4, Section F), and Procedure is
// replaced by an optional Notes field (OWNER DECISION 5).
describe("CreatePMScheduleModal", () => {
  it("renders nothing when closed", () => {
    render(<CreatePMScheduleModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(screen.queryByText("Create PM Schedule")).toBeNull();
  });

  it("renders every form field when open, with no Schedule Code or Checklist Template input", () => {
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(screen.getByLabelText("Equipment")).toBeTruthy();
    expect(screen.getByLabelText("Frequency")).toBeTruthy();
    expect(screen.getByLabelText("Trigger Type")).toBeTruthy();
    expect(screen.getByLabelText("Start Date")).toBeTruthy();
    expect(screen.getByLabelText("Technician")).toBeTruthy();
    expect(screen.getByLabelText("Estimated Duration")).toBeTruthy();
    expect(screen.getByLabelText("Notes")).toBeTruthy();
    expect(screen.getByText("Planned Activities")).toBeTruthy();

    expect(screen.queryByLabelText("Schedule Code")).toBeNull();
    expect(screen.queryByLabelText("Procedure")).toBeNull();
    expect(screen.queryByLabelText("Checklist Template")).toBeNull();
  });

  it("does not call onCreate when Equipment is empty", () => {
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).not.toHaveBeenCalled();
  });

  it("calls onCreate with the resolved form values, and no planned activities when none are selected", () => {
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Frequency"), { target: { value: "WEEKLY" } });
    fireEvent.change(screen.getByLabelText("Trigger Type"), { target: { value: "METER" } });
    fireEvent.change(screen.getByLabelText("Technician"), { target: { value: "Bagus Setiawan" } });
    fireEvent.change(screen.getByLabelText("Start Date"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("Estimated Duration"), { target: { value: "2.5" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Bring spare gasket" } });

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).toHaveBeenCalledWith({
      equipmentTag: "533-P-1",
      frequency: "WEEKLY",
      triggerType: "METER",
      assignedTechnician: "Bagus Setiawan",
      startDate: "2026-08-01",
      estimatedDurationHours: 2.5,
      notes: "Bring spare gasket",
      plannedActivities: null,
    });
  });

  it("includes explicitly checked planned activities, with no `done` field, in the {family, variant, code} shape", () => {
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));
    fireEvent.click(screen.getByLabelText("Reservoir"));

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).toHaveBeenCalledOnce();
    const payload = onCreate.mock.calls[0][0];
    expect(payload.plannedActivities).toEqual([
      { family: "Flushing Line", variant: "DE", code: "FLUSHING_LINE_DE" },
      { family: "Reservoir", variant: "GENERAL", code: "RESERVOIR" },
    ]);
    for (const entry of payload.plannedActivities) {
      expect(entry).not.toHaveProperty("done");
    }
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={onClose} onCreate={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
