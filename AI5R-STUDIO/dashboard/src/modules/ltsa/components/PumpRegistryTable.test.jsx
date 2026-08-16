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
    criticality: "HIGH",
    openWO: 0,
    status: "RUNNING",
  },
  {
    code: "PMP-002",
    tag: "211-P-1B",
    name: "Boiler Feedwater Pump 1B",
    manufacturer: "Sulzer",
    area: "Boiler House",
    criticality: "MEDIUM",
    openWO: 0,
    status: "STANDBY",
  },
];

describe("PumpRegistryTable", () => {
  it("renders the maintenance-oriented columns", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    ["Pump", "Area", "Criticality", "Open Work Orders", "Status"].forEach((header) => {
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

  it("renders a criticality badge for each pump with real criticality data", () => {
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("HIGH")).toBeTruthy();
    expect(screen.getByText("MEDIUM")).toBeTruthy();
  });

  it("shows a dash instead of fabricating criticality when the field is missing", () => {
    render(
      <PumpRegistryTable
        pumps={[{ ...PUMPS[0], criticality: null }]}
        selectedCode={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText("—")).toBeTruthy();
  });

  it("renders an empty state instead of a bare table when no pumps match", () => {
    render(<PumpRegistryTable pumps={[]} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText(/no pumps match/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("marks table rows as keyboard-focusable and activates onSelect via Enter", () => {
    const onSelect = vi.fn();
    render(<PumpRegistryTable pumps={PUMPS} selectedCode={null} onSelect={onSelect} />);

    const rows = screen.getAllByRole("row");
    expect(rows[1].getAttribute("tabIndex")).toBe("0");

    fireEvent.keyDown(rows[1], { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("PMP-001");
  });
});
