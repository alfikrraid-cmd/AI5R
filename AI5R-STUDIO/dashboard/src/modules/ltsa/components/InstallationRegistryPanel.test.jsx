import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import InstallationRegistryPanel from "./InstallationRegistryPanel";

const INSTALLATIONS = [
  {
    id: "INSTL-001-2026",
    pumpTagNumber: "211-P-14B",
    plantEquipNo: "211-P-14B",
    area: "HCC",
    date: "January 06, 2026",
    sealType: "T15W",
    assemblyGpn: null,
    drawingNo: "E12914",
    sourceDocumentName: "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf",
  },
  {
    id: "INSTL-002-2026",
    pumpTagNumber: "212-P-25A",
    plantEquipNo: "212-P-25A",
    area: null,
    date: "January 20, 2026",
    sealType: null,
    assemblyGpn: null,
    drawingNo: null,
    sourceDocumentName: "SCAN 002 INSTALLATION REPORT 212-P-25A.pdf",
  },
];

describe("InstallationRegistryPanel", () => {
  it("renders one row per installation with the required columns", () => {
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={() => {}} />);
    expect(screen.getByText("211-P-14B")).toBeTruthy();
    expect(screen.getByText("212-P-25A")).toBeTruthy();
    expect(screen.getByText("HCC")).toBeTruthy();
    expect(screen.getByText("T15W")).toBeTruthy();
    expect(screen.getByText("E12914")).toBeTruthy();
  });

  it("renders N/A (never blank, never fabricated) for missing area/seal type/drawing/GPN", () => {
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={() => {}} />);
    // INSTL-002-2026 has area/sealType/drawingNo/assemblyGpn all null --
    // at least 4 "N/A" cells must render for that one row alone.
    expect(screen.getAllByText("N/A").length).toBeGreaterThanOrEqual(4);
  });

  it("filters by pump tag search", () => {
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search pump tag, seal type/i), { target: { value: "211-P-14B" } });
    expect(screen.getByText("211-P-14B")).toBeTruthy();
    expect(screen.queryByText("212-P-25A")).toBeNull();
  });

  it("filters by seal type search", () => {
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search pump tag, seal type/i), { target: { value: "T15W" } });
    expect(screen.getByText("211-P-14B")).toBeTruthy();
    expect(screen.queryByText("212-P-25A")).toBeNull();
  });

  it("shows an honest empty message when the search matches nothing, never a fabricated row", () => {
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search pump tag, seal type/i), { target: { value: "no-such-pump" } });
    expect(screen.getByText(/no installation reports match/i)).toBeTruthy();
  });

  it("calls onSelectInstallation with the installation id when a row is clicked", () => {
    const onSelect = vi.fn();
    render(<InstallationRegistryPanel installations={INSTALLATIONS} selectedInstallationId={null} onSelectInstallation={onSelect} />);
    fireEvent.click(screen.getByText("211-P-14B").closest("tr"));
    expect(onSelect).toHaveBeenCalledWith("INSTL-001-2026");
  });
});
