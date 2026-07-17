import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PumpRegistryTable from "./PumpRegistryTable";

const PUMPS = [
  {
    code: "PMP-001",
    tag: "211-P-1A",
    name: "Boiler Feedwater Pump 1A",
    manufacturer: "Sulzer",
    type: "Centrifugal",
    status: "ACTIVE",
  },
  {
    code: "PMP-002",
    tag: "211-P-1B",
    name: "Boiler Feedwater Pump 1B",
    manufacturer: "Sulzer",
    type: "Centrifugal",
    status: "STANDBY",
  },
];

describe("PumpRegistryTable", () => {
  it("renders the required columns", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    ["Code", "Tag", "Name", "Manufacturer", "Type", "Status"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per pump", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("PMP-001")).toBeTruthy();
    expect(screen.getByText("Boiler Feedwater Pump 1B")).toBeTruthy();
  });

  it("calls onSelect with the clicked pump's code", () => {
    const onSelect = vi.fn();
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("PMP-002"));

    expect(onSelect).toHaveBeenCalledWith("PMP-002");
  });

  it("marks the selected row", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode="PMP-002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });
});
