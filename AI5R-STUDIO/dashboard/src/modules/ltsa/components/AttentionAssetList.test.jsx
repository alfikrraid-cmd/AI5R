import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AttentionAssetList from "./AttentionAssetList";

const ASSETS = [
  {
    pump: "Sour Water Stripper Bottoms Pump",
    tag: "641-P-5",
    criticality: "HIGH",
    status: "FAULT",
    openWorkOrders: 1,
    lastCorrectiveMaintenance: "2026-07-18",
  },
  {
    pump: "Boiler Feedwater Pump 1A",
    tag: "211-P-1A",
    criticality: "HIGH",
    status: "RUNNING",
    openWorkOrders: 1,
    lastCorrectiveMaintenance: null,
  },
];

describe("AttentionAssetList", () => {
  it("renders a summary row per asset requiring attention", () => {
    render(<AttentionAssetList assets={ASSETS} />);

    expect(screen.getByRole("heading", { name: "Assets Requiring Attention" })).toBeTruthy();
    expect(screen.getByText("Sour Water Stripper Bottoms Pump")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("FAULT")).toBeTruthy();
    expect(screen.getByText("2026-07-18")).toBeTruthy();
  });

  it("renders a fallback when an asset has no recorded corrective maintenance", () => {
    render(<AttentionAssetList assets={ASSETS} />);

    expect(screen.getByText("None recorded")).toBeTruthy();
  });

  it("renders a reassuring empty state when no asset requires attention", () => {
    render(<AttentionAssetList assets={[]} />);

    expect(screen.getByText(/no assets currently require attention/i)).toBeTruthy();
  });
});
