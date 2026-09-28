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

// Merged registry (V1 unified columns + unified-RC Seal ID): look a cell up by
// its column header so each assertion targets one column's contract.
function cellFor(rowText, header) {
  const headers = screen.getAllByRole("columnheader").map((th) => th.textContent);
  const col = headers.indexOf(header);
  const row = screen.getByText(rowText).closest("tr");
  return row.cells[col];
}

describe("SealRegistryTable", () => {
  it("renders the required columns", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    ["Seal ID", "Mechanical Seal", "Size", "GPN / Drawing", "Compatible Pumps", "Available Stock", "Status", "Action"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per seal, using the professional Seal ID, never the legacy code", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    expect(screen.getByText("MS-JC-0001")).toBeTruthy();
    expect(screen.getByText("MS-JC-0002")).toBeTruthy();
    // The legacy LTSA-SEAL-* code is never shown under the Seal ID header.
    expect(cellFor("MS-JC-0001", "Seal ID").textContent).toBe("MS-JC-0001");
    expect(cellFor("MS-JC-0001", "Seal ID").textContent).not.toContain("LTSA-SEAL-T48LP-2-3-4");
  });

  it("renders an honest placeholder for a null GPN, never blank or fabricated", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={() => {}} />);

    expect(cellFor("MS-JC-0001", "GPN / Drawing").textContent).toBe("—");
    expect(cellFor("MS-JC-0002", "GPN / Drawing").textContent).toContain("GPN-12345");
  });

  it("renders N/A for the Seal ID when a seal has not been assigned one, never falling back to the legacy code", () => {
    const seals = [{ ...SEALS[0], sealId: null }];
    render(<SealRegistryTable seals={seals} selectedCode={null} onSelect={() => {}} />);

    const headers = screen.getAllByRole("columnheader").map((th) => th.textContent);
    const idCell = screen.getAllByRole("row")[1].cells[headers.indexOf("Seal ID")];
    expect(idCell.textContent).toBe("N/A");
    expect(idCell.textContent).not.toContain(seals[0].code);
  });

  it("calls onSelect with the clicked seal's code", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("MS-JC-0002"));

    expect(onSelect).toHaveBeenCalledWith("LTSA-SEAL-5610VQ-2-1-4");
  });

  it("calls onSelect exactly once with the clicked seal identity when Details button is clicked", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    expect(detailsButtons).toHaveLength(2);

    expect(() => fireEvent.click(detailsButtons[1])).not.toThrow();
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("LTSA-SEAL-5610VQ-2-1-4");
  });

  it("does not trigger duplicate selection via row bubbling when Details button is clicked", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    fireEvent.click(detailsButtons[0]);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("LTSA-SEAL-T48LP-2-3-4");
  });

  it("resolves the same seal identity whether row or Details button is clicked", () => {
    const onSelectRow = vi.fn();
    const { unmount } = render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelectRow} />);
    fireEvent.click(screen.getByText("MS-JC-0001"));
    expect(onSelectRow).toHaveBeenCalledWith("LTSA-SEAL-T48LP-2-3-4");
    unmount();

    const onSelectButton = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelectButton} />);
    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    fireEvent.click(detailsButtons[0]);
    expect(onSelectButton).toHaveBeenCalledWith("LTSA-SEAL-T48LP-2-3-4");
  });

  it("marks the selected row", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode="LTSA-SEAL-5610VQ-2-1-4" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });
});
