import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreatePMScheduleModal from "./CreatePMScheduleModal";

describe("CreatePMScheduleModal", () => {
  it("renders nothing when closed", () => {
    render(<CreatePMScheduleModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(screen.queryByText("Create PM Schedule")).toBeNull();
  });

  it("renders every form field when open", () => {
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(screen.getByLabelText("Equipment")).toBeTruthy();
    expect(screen.getByLabelText("Frequency")).toBeTruthy();
    expect(screen.getByLabelText("Trigger Type")).toBeTruthy();
    expect(screen.getByLabelText("Technician")).toBeTruthy();
    expect(screen.getByLabelText("Start Date")).toBeTruthy();
    expect(screen.getByLabelText("Estimated Duration")).toBeTruthy();
    expect(screen.getByLabelText("Checklist Template")).toBeTruthy();
  });

  it("does not call onCreate when Equipment is empty", () => {
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).not.toHaveBeenCalled();
  });

  it("calls onCreate with the resolved form values, including the checklist template's items", () => {
    const onCreate = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Frequency"), { target: { value: "WEEKLY" } });
    fireEvent.change(screen.getByLabelText("Trigger Type"), { target: { value: "METER" } });
    fireEvent.change(screen.getByLabelText("Technician"), { target: { value: "Bagus Setiawan" } });
    fireEvent.change(screen.getByLabelText("Start Date"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("Estimated Duration"), { target: { value: "2.5" } });
    fireEvent.change(screen.getByLabelText("Checklist Template"), {
      target: { value: "Seal Inspection Checklist" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(onCreate).toHaveBeenCalledWith({
      equipmentTag: "533-P-1",
      frequency: "WEEKLY",
      triggerType: "METER",
      assignedTechnician: "Bagus Setiawan",
      startDate: "2026-08-01",
      estimatedDurationHours: 2.5,
      checklistTemplate: "Seal Inspection Checklist",
      checklist: [
        "Inspect seal chamber for leakage",
        "Check seal flush pressure",
        "Record vibration and temperature readings",
      ],
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<CreatePMScheduleModal isOpen onClose={onClose} onCreate={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
