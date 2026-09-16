import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SealRegistryTable from "./SealRegistryTable";

// MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 Part B -- registry columns are
// now Seal ID | GPN | Seal Type | Size | Manufacturer | Status (Seal
// Code/Name dropped from the visible table, not deleted from the domain
// -- see sealMapping.js/Seal.jsx for where they remain real and used).
const SEALS = [
  {
    code: "LTSA-SEAL-T48LP-2-3-4",
    sealId: "MS-JC-0001",
    name: "John Crane Type 21",
    type: "T48LP",
    gpnJohnCrane: null,
    shaftSize: 2.75,
    manufacturer: "John Crane",
    status: "ACTIVE",
  },
  {
    code: "LTSA-SEAL-5610VQ-2-1-4",
    sealId: "MS-JC-0002",
    name: "John Crane Type 1",
    type: "5610VQ",
    gpnJohnCrane: "GPN-12345",
    shaftSize: 2.25,
    manufacturer: "John Crane",
    status: "STANDBY",
  },
];

describe("SealRegistryTable", () => {
  it("renders the required columns", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    ["Seal ID", "GPN", "Seal Type", "Size", "Manufacturer", "Status"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per seal, using the professional Seal ID, never the legacy code", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("MS-JC-0001")).toBeTruthy();
    expect(screen.getByText("MS-JC-0002")).toBeTruthy();
    expect(screen.queryByText("LTSA-SEAL-T48LP-2-3-4")).toBeNull();
  });

  it("renders N/A for a null GPN, never blank or fabricated", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("N/A")).toBeTruthy();
    expect(screen.getByText("GPN-12345")).toBeTruthy();
  });

  it("renders N/A for the Seal ID when a seal has not been assigned one, never falling back to the legacy code", () => {
    const seals = [{ ...SEALS[0], sealId: null }];
    render(<SealRegistryTable seals={seals} selectedCode={null} onSelect={() => {}} />);

    const idCell = screen.getAllByText("N/A")[0];
    expect(idCell).toBeTruthy();
    expect(screen.queryByText(seals[0].code)).toBeNull();
  });

  it("calls onSelect with the clicked seal's code", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("MS-JC-0002"));

    expect(onSelect).toHaveBeenCalledWith("LTSA-SEAL-5610VQ-2-1-4");
  });

  it("marks the selected row", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode="LTSA-SEAL-5610VQ-2-1-4" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });
});
