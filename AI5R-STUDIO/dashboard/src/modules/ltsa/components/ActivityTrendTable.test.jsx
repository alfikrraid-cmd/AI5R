import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ActivityTrendTable from "./ActivityTrendTable";

const TREND = {
  buckets: [
    { label: "4 Weeks Ago", pmCount: 1, cmCount: 0, woCount: 1, total: 2 },
    { label: "3 Weeks Ago", pmCount: 0, cmCount: 1, woCount: 0, total: 1 },
    { label: "2 Weeks Ago", pmCount: 1, cmCount: 1, woCount: 2, total: 4 },
    { label: "This Week", pmCount: 2, cmCount: 3, woCount: 3, total: 8 },
  ],
  correctiveMaintenanceDirection: "UP",
};

describe("ActivityTrendTable", () => {
  it("renders the trend heading and every weekly bucket", () => {
    render(<ActivityTrendTable trend={TREND} />);

    expect(screen.getByRole("heading", { name: "Maintenance Activity Trend" })).toBeTruthy();
    expect(screen.getByText("4 Weeks Ago")).toBeTruthy();
    expect(screen.getByText("This Week")).toBeTruthy();
    expect(screen.getByText("8")).toBeTruthy();
  });

  it("renders the corrective maintenance direction badge", () => {
    render(<ActivityTrendTable trend={TREND} />);

    expect(screen.getByText("▲ Rising")).toBeTruthy();
  });

  it("renders a falling badge when the direction is DOWN", () => {
    render(<ActivityTrendTable trend={{ ...TREND, correctiveMaintenanceDirection: "DOWN" }} />);

    expect(screen.getByText("▼ Falling")).toBeTruthy();
  });

  it("renders a stable badge when the direction is FLAT", () => {
    render(<ActivityTrendTable trend={{ ...TREND, correctiveMaintenanceDirection: "FLAT" }} />);

    expect(screen.getByText("▬ Stable")).toBeTruthy();
  });
});
