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

  describe("search filtering (AI5R-CMON-UX-001)", () => {
    it("filters options by a partial canonical tag search", () => {
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "211" } });

      expect(screen.getByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeTruthy();
      expect(screen.queryByRole("option", { name: "641-P-5 — Sour Water Stripper Bottoms Pump" })).toBeNull();
    });

    it("finds a canonical tag from a compact, punctuation-free search query", () => {
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "211p1a" } });

      expect(screen.getByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeTruthy();
    });

    it("finds a pump by searching its name/description", () => {
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "sour water" } });

      expect(screen.getByRole("option", { name: "641-P-5 — Sour Water Stripper Bottoms Pump" })).toBeTruthy();
      expect(screen.queryByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeNull();
    });

    it("shows a no-results state when nothing matches", () => {
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "zzz-not-a-pump" } });

      expect(screen.getByRole("status").textContent).toContain("No pumps match");
      expect(screen.queryByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeNull();
    });

    it("selecting a filtered result reports the canonical tag, never the search text", () => {
      const onSelect = vi.fn();
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={onSelect} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "211p1a" } });
      fireEvent.change(screen.getByRole("combobox"), { target: { value: "211-P-1A" } });

      expect(onSelect).toHaveBeenCalledWith("211-P-1A");
      expect(onSelect).not.toHaveBeenCalledWith("211p1a");
    });

    it("an empty search shows every asset again (unchanged default behavior)", () => {
      render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "211" } });
      fireEvent.change(screen.getByLabelText("Search tag or name"), { target: { value: "" } });

      expect(screen.getByRole("option", { name: "211-P-1A — Boiler Feedwater Pump 1A" })).toBeTruthy();
      expect(screen.getByRole("option", { name: "641-P-5 — Sour Water Stripper Bottoms Pump" })).toBeTruthy();
    });
  });

  it("no longer fixes a hardcoded 320px minWidth (fits small viewports)", () => {
    render(<AssetSelector assets={ASSETS} selectedTag={null} onSelect={() => {}} />);

    const select = screen.getByRole("combobox");
    expect(select.style.minWidth).not.toBe("320px");
    expect(select.style.width).toBe("100%");
  });
});
