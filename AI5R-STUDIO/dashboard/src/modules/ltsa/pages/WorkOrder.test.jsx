import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WorkOrder from "./WorkOrder";
import sampleWorkOrders from "../data/sampleWorkOrders";

describe("Work Order workspace page", () => {
  it("renders the page header", () => {
    render(<WorkOrder />);

    expect(screen.getByRole("heading", { name: "Work Order Workspace" })).toBeTruthy();
  });

  it("renders every sample work order in the registry table", () => {
    render(<WorkOrder />);

    sampleWorkOrders.forEach((workOrder) => {
      expect(screen.getByText(workOrder.id)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any work order is selected", () => {
    render(<WorkOrder />);

    expect(screen.getByText(/no work order selected/i)).toBeTruthy();
  });

  it("shows the selected work order's detail when a registry row is clicked", () => {
    render(<WorkOrder />);

    fireEvent.click(screen.getByText("WO-1002"));

    expect(
      screen.getByRole("heading", { name: "Quarterly vibration survey" })
    ).toBeTruthy();
  });

  it("filters the registry table by search text", () => {
    render(<WorkOrder />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "vibration" } });

    expect(screen.getByText("WO-1002")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<WorkOrder />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "COMPLETED" } });

    expect(screen.getByText("WO-1008")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
  });

  it("shows an empty state in the registry when no work order matches the search", () => {
    render(<WorkOrder />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-work-order-xyz" } });

    expect(screen.getByText(/no work orders match/i)).toBeTruthy();
  });

  it("opens the Create Work Order modal when the header action is clicked", () => {
    render(<WorkOrder />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create Work Order" }));

    expect(screen.getByRole("heading", { name: "Create Work Order" })).toBeTruthy();
  });

  it("creates a new work order via the modal, closes it, and selects the new entry", () => {
    render(<WorkOrder />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create Work Order" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Inspect coupling" } });

    fireEvent.click(screen.getByRole("button", { name: "Create Work Order" }));

    expect(screen.queryByRole("heading", { name: "Create Work Order" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Inspect coupling" })).toBeTruthy();
    expect(screen.getAllByText("Inspect coupling")).toHaveLength(2);
    expect(screen.getByRole("status").textContent).toContain("WO-1009 created.");
  });
});
