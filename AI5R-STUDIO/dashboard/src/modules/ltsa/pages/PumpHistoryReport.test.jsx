import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PumpHistoryReport from "./PumpHistoryReport";
import samplePumps from "../data/samplePumps";

describe("Pump History Report", () => {
  it("renders the report header and print button", () => {
    render(<PumpHistoryReport />);

    expect(screen.getByRole("heading", { name: "Pump History Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("renders an Asset Summary card for every pump", () => {
    render(<PumpHistoryReport />);

    expect(screen.getAllByRole("heading", { name: "Asset Summary" })).toHaveLength(samplePumps.length);
    samplePumps.forEach((pump) => {
      expect(screen.getByText(pump.tag)).toBeTruthy();
    });
  });
});
