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

    ["Mechanical Seal", "Size", "GPN / Drawing", "Compatible Pumps", "Available Stock", "Status", "Action"].forEach((header) => {
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

  it("calls onSelect exactly once with the clicked seal identity when Details button is clicked", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    expect(detailsButtons).toHaveLength(2);

    expect(() => fireEvent.click(detailsButtons[1])).not.toThrow();
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("SC-002");
  });

  it("does not trigger duplicate selection via row bubbling when Details button is clicked", () => {
    const onSelect = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelect} />);

    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    fireEvent.click(detailsButtons[0]);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("SC-001");
  });

  it("resolves the same seal identity whether row or Details button is clicked", () => {
    const onSelectRow = vi.fn();
    const { unmount } = render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelectRow} />);
    fireEvent.click(screen.getByText("SC-001"));
    expect(onSelectRow).toHaveBeenCalledWith("SC-001");
    unmount();

    const onSelectButton = vi.fn();
    render(<SealRegistryTable seals={SEALS} selectedCode={null} onSelect={onSelectButton} />);
    const detailsButtons = screen.getAllByRole("button", { name: "Details" });
    fireEvent.click(detailsButtons[0]);
    expect(onSelectButton).toHaveBeenCalledWith("SC-001");
  });

  it("marks the selected row", () => {
    render(<SealRegistryTable seals={SEALS} selectedCode="SC-002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });
});
