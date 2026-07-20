import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreateCMReportModal from "./CreateCMReportModal";

describe("CreateCMReportModal", () => {
  it("renders nothing when closed", () => {
    render(<CreateCMReportModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(screen.queryByText("Create Corrective Maintenance Report")).toBeNull();
  });

  it("renders every form field when open", () => {
    render(<CreateCMReportModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(screen.getByLabelText("Equipment")).toBeTruthy();
    expect(screen.getByLabelText("Failure Category")).toBeTruthy();
    expect(screen.getByLabelText("Severity")).toBeTruthy();
    expect(screen.getByLabelText("Priority")).toBeTruthy();
    expect(screen.getByLabelText("Failure Description")).toBeTruthy();
    expect(screen.getByLabelText("Immediate Action")).toBeTruthy();
    expect(screen.getByLabelText("Assigned Technician")).toBeTruthy();
  });

  it("does not call onCreate when Equipment or Failure Description is empty", () => {
    const onCreate = vi.fn();
    render(<CreateCMReportModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onCreate).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onCreate).not.toHaveBeenCalled();
  });

  it("calls onCreate with the form values when submitted", () => {
    const onCreate = vi.fn();
    render(<CreateCMReportModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Failure Category"), { target: { value: "ELECTRICAL" } });
    fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "MAJOR" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "HIGH" } });
    fireEvent.change(screen.getByLabelText("Failure Description"), {
      target: { value: "Pump tripped on motor overload." },
    });
    fireEvent.change(screen.getByLabelText("Immediate Action"), {
      target: { value: "Reset overload, monitor for repeat trip." },
    });
    fireEvent.change(screen.getByLabelText("Assigned Technician"), { target: { value: "Bagus Setiawan" } });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onCreate).toHaveBeenCalledWith({
      equipmentTag: "533-P-1",
      failureCategory: "ELECTRICAL",
      severity: "MAJOR",
      priority: "HIGH",
      failureDescription: "Pump tripped on motor overload.",
      immediateAction: "Reset overload, monitor for repeat trip.",
      assignedTechnician: "Bagus Setiawan",
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<CreateCMReportModal isOpen onClose={onClose} onCreate={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
