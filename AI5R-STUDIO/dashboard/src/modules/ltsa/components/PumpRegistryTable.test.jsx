import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PumpRegistryTable from "./PumpRegistryTable";

const PUMPS = [
  {
    code: "PMP-001",
    tag: "211-P-1A",
    name: "Boiler Feedwater Pump 1A",
    manufacturer: "Sulzer",
    area: "Boiler House",
    healthScore: 92,
    nextPM: "2026-10-02",
    openWO: 0,
    status: "RUNNING",
  },
  {
    code: "PMP-002",
    tag: "211-P-1B",
    name: "Boiler Feedwater Pump 1B",
    manufacturer: "Sulzer",
    area: "Boiler House",
    healthScore: 88,
    nextPM: "2026-09-15",
    openWO: 0,
    status: "STANDBY",
  },
];

describe("PumpRegistryTable", () => {
  it("renders the maintenance-oriented columns", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    ["Pump", "Area", "Health Score", "Next PM", "Open Work Orders", "Status"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per pump with tag/name/manufacturer grouped under Pump", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("211-P-1A")).toBeTruthy();
    expect(screen.getByText("Boiler Feedwater Pump 1B")).toBeTruthy();
    expect(screen.getAllByText("Sulzer")).toHaveLength(2);
  });

  it("calls onSelect with the clicked pump's code", () => {
    const onSelect = vi.fn();
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("211-P-1B"));

    expect(onSelect).toHaveBeenCalledWith("PMP-002");
  });

  it("marks the selected row", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode="PMP-002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });

  it("renders a status badge for each pump", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("RUNNING")).toBeTruthy();
    expect(screen.getByText("STANDBY")).toBeTruthy();
  });

  it("color-codes the health score", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("92").style.color).not.toBe("");
    expect(screen.getByText("88").style.color).not.toBe("");
  });

  it("renders an empty state instead of a bare table when no pumps match", () => {
    render(<PumpRegistryTable pumps={[]} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText(/no pumps match/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
