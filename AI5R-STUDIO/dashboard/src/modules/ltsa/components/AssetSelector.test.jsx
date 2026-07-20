import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AssetSelector from "./AssetSelector";

const ASSETS = [
  { code: "PMP-001", tag: "211-P-1A", name: "Boiler Feedwater Pump 1A" },
  { code: "PMP-009", tag: "641-P-5", name: "Sour Water Stripper Bottoms Pump" },
];

describe("AssetSelector", () => {
  it("renders a placeholder plus every asset option", () => {
    render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

    expect(screen.getByRole("option", { name: "Select a pump..." })).toBeTruthy();
    expect(screen.getByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeTruthy();
    expect(
      screen.getByRole("option", { name: "641-P-5 — Sour Water Stripper Bottoms Pump" })
    ).toBeTruthy();
  });

  it("reflects the selected tag", () => {
    render(<AssetSelector assets={ASSETS} selectedTag="641-P-5" onSelect={() => {}} />);

    expect(screen.getByRole("combobox").value).toBe("641-P-5");
  });

  it("calls onSelect with the chosen tag", () => {
    const onSelect = vi.fn();
    render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={onSelect} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "641-P-5" } });

    expect(onSelect).toHaveBeenCalledWith("641-P-5");
  });

  it("calls onSelect with null when the placeholder is chosen", () => {
    const onSelect = vi.fn();
    render(<AssetSelector assets={ASSETS} selectedTag="641-P-5" onSelect={onSelect} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "" } });

    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
