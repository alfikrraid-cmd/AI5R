import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import WorkOrderRegistryTable from "./WorkOrderRegistryTable";

const WORK_ORDERS = [
  {
    id: "WO-1001",
    title: "Seal replacement — repeat failures",
    equipmentTag: "641-P-5",
    area: "SWS Unit",
    priority: "CRITICAL",
    assignedTechnician: "Dedi Kurniawan",
    dueDate: "2026-07-21",
    status: "OPEN",
  },
  {
    id: "WO-1002",
    title: "Quarterly vibration survey",
    equipmentTag: "211-P-1A",
    area: "Boiler House",
    priority: "MEDIUM",
    assignedTechnician: "Sari Wulandari",
    dueDate: "2026-07-24",
    status: "IN_PROGRESS",
  },
];

describe("WorkOrderRegistryTable", () => {
  it("renders the work order columns", () => {
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId={null} onSelect={() => {}} />);

    ["Work Order", "Equipment", "Priority", "Assigned Technician", "Due Date", "Status"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per work order with id/title grouped under Work Order", () => {
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("Quarterly vibration survey")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
  });

  it("calls onSelect with the clicked work order's id", () => {
    const onSelect = vi.fn();
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("WO-1002"));

    expect(onSelect).toHaveBeenCalledWith("WO-1002");
  });

  it("marks the selected row", () => {
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId="WO-1002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });

  it("renders a priority badge and a status badge for each work order", () => {
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("CRITICAL")).toBeTruthy();
    expect(screen.getByText("MEDIUM")).toBeTruthy();
    expect(screen.getByText("Open")).toBeTruthy();
    expect(screen.getByText("In Progress")).toBeTruthy();
  });

  it("renders an empty state instead of a bare table when no work orders match", () => {
    render(<WorkOrderRegistryTable workOrders={[]} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText(/no work orders match/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("marks table rows as keyboard-focusable and activates onSelect via Enter", () => {
    const onSelect = vi.fn();
    render(<WorkOrderRegistryTable workOrders={WORK_ORDERS} selectedId={null} onSelect={onSelect} />);

    const rows = screen.getAllByRole("row");
    expect(rows[1].getAttribute("tabIndex")).toBe("0");

    fireEvent.keyDown(rows[1], { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("WO-1001");
  });
});
