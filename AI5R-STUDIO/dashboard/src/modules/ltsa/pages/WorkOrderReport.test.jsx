import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WorkOrderReport from "./WorkOrderReport";
import sampleWorkOrders from "../data/sampleWorkOrders";

describe("Work Order Report", () => {
  it("renders the report header and print button", () => {
    render(<WorkOrderReport />);

    expect(screen.getByRole("heading", { name: "Work Order Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("renders every sample work order via the reused registry table", () => {
    render(<WorkOrderReport />);

    expect(screen.getByRole("columnheader", { name: "Work Order" })).toBeTruthy();
    sampleWorkOrders.forEach((wo) => {
      expect(screen.getByText(wo.id)).toBeTruthy();
    });
  });
});
