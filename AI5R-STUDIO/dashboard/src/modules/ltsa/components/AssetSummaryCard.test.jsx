import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AssetSummaryCard from "./AssetSummaryCard";

const SUMMARY = {
  pump: "Sour Water Stripper Bottoms Pump",
  tag: "641-P-5",
  area: "SWS Unit",
  status: "FAULT",
  criticality: "HIGH",
  lastPreventiveMaintenance: "2025-12-10",
  lastCorrectiveMaintenance: "2026-07-18",
  openWorkOrders: 1,
  lastActivity: "2026-07-19",
};

describe("AssetSummaryCard", () => {
  it("renders every summary field", () => {
    render(<AssetSummaryCard summary={SUMMARY} />);

    expect(screen.getByRole("heading", { name: "Asset Summary" })).toBeTruthy();
    expect(screen.getByText("Sour Water Stripper Bottoms Pump")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("SWS Unit")).toBeTruthy();
    expect(screen.getByText("FAULT")).toBeTruthy();
    expect(screen.getByText("HIGH")).toBeTruthy();
    expect(screen.getByText("2025-12-10")).toBeTruthy();
    expect(screen.getByText("2026-07-18")).toBeTruthy();
    expect(screen.getByText("2026-07-19")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders fallbacks when there is no maintenance history", () => {
    render(
      <AssetSummaryCard
        summary={{
          ...SUMMARY,
          lastPreventiveMaintenance: null,
          lastCorrectiveMaintenance: null,
          lastActivity: null,
          openWorkOrders: 0,
        }}
      />
    );

    expect(screen.getAllByText("None recorded")).toHaveLength(2);
    expect(screen.getByText("No recorded activity")).toBeTruthy();
  });
});
