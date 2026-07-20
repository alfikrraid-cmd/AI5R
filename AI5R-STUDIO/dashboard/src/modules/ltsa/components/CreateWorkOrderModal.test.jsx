import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreateWorkOrderModal from "./CreateWorkOrderModal";

describe("CreateWorkOrderModal", () => {
  it("renders nothing when closed", () => {
    render(<CreateWorkOrderModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);

    expect(screen.queryByText("Create Work Order")).toBeNull();
  });

  it("renders every form field when open", () => {
    render(<CreateWorkOrderModal isOpen onClose={() => {}} onCreate={() => {}} />);

    expect(screen.getByLabelText("Title")).toBeTruthy();
    expect(screen.getByLabelText("Equipment Tag")).toBeTruthy();
    expect(screen.getByLabelText("Area")).toBeTruthy();
    expect(screen.getByLabelText("Work Type")).toBeTruthy();
    expect(screen.getByLabelText("Priority")).toBeTruthy();
    expect(screen.getByLabelText("Assigned To")).toBeTruthy();
    expect(screen.getByLabelText("Due Date")).toBeTruthy();
    expect(screen.getByLabelText("Description")).toBeTruthy();
  });

  it("does not call onCreate when the title is empty", () => {
    const onCreate = vi.fn();
    render(<CreateWorkOrderModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: "Create Work Order" }));

    expect(onCreate).not.toHaveBeenCalled();
  });

  it("calls onCreate with the form values when submitted", () => {
    const onCreate = vi.fn();
    render(<CreateWorkOrderModal isOpen onClose={() => {}} onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Inspect coupling" } });
    fireEvent.change(screen.getByLabelText("Equipment Tag"), { target: { value: "211-P-1A" } });
    fireEvent.change(screen.getByLabelText("Area"), { target: { value: "Boiler House" } });
    fireEvent.change(screen.getByLabelText("Work Type"), { target: { value: "INSPECTION" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "HIGH" } });
    fireEvent.change(screen.getByLabelText("Assigned To"), { target: { value: "Sari Wulandari" } });
    fireEvent.change(screen.getByLabelText("Due Date"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Coupling wear check." } });

    fireEvent.click(screen.getByRole("button", { name: "Create Work Order" }));

    expect(onCreate).toHaveBeenCalledWith({
      title: "Inspect coupling",
      equipmentTag: "211-P-1A",
      area: "Boiler House",
      workType: "INSPECTION",
      priority: "HIGH",
      assignedTo: "Sari Wulandari",
      dueDate: "2026-08-01",
      description: "Coupling wear check.",
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<CreateWorkOrderModal isOpen onClose={onClose} onCreate={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
