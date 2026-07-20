import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CriticalityDistributionList from "./CriticalityDistributionList";

describe("CriticalityDistributionList", () => {
  it("renders a badge per criticality level with its count", () => {
    render(
      <CriticalityDistributionList
        distribution={[
          { criticality: "HIGH", count: 7 },
          { criticality: "MEDIUM", count: 6 },
        ]}
      />
    );

    expect(screen.getByRole("heading", { name: "Asset Criticality Distribution" })).toBeTruthy();
    expect(screen.getByText("HIGH: 7")).toBeTruthy();
    expect(screen.getByText("MEDIUM: 6")).toBeTruthy();
  });

  it("renders nothing extra when a criticality level is absent", () => {
    render(<CriticalityDistributionList distribution={[{ criticality: "HIGH", count: 13 }]} />);

    expect(screen.queryByText(/MEDIUM/)).toBeNull();
    expect(screen.queryByText(/LOW/)).toBeNull();
  });
});
