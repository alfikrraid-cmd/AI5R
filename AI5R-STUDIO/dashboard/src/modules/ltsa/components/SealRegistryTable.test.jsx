import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SealRegistryTable from "./SealRegistryTable";

const SEALS = [
  {
    code: "SC-001",
    name: "John Crane Type 21",
    type: "Single Mechanical Seal",
    manufacturer: "John Crane",
    status: "ACTIVE",
  },
  {
    code: "SC-002",
    name: "John Crane Type 1",
    type: "Single Mechanical Seal",
    manufacturer: "John Crane",
    status: "STANDBY",
  },
];

describe("SealRegistryTable", () => {
  it("renders the required columns", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    ["Seal Code", "Name", "Type", "Manufacturer", "Status"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per seal", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("SC-001")).toBeTruthy();
    expect(screen.getByText("John Crane Type 1")).toBeTruthy();
  });

  it("calls onSelect with the clicked seal's code", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("SC-002"));

    expect(onSelect).toHaveBeenCalledWith("SC-002");
  });

  it("marks the selected row", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode="SC-002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });
});
