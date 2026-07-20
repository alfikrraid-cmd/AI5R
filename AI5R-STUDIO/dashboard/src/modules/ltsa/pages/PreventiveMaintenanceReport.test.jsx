import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PreventiveMaintenanceReport from "./PreventiveMaintenanceReport";
import samplePMSchedules from "../data/samplePMSchedules";

describe("Preventive Maintenance Report", () => {
  it("renders the report header and print button", () => {
    render(<PreventiveMaintenanceReport />);

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("renders every sample PM schedule via the reused schedule table", () => {
    render(<PreventiveMaintenanceReport />);

    expect(screen.getByRole("columnheader", { name: "PM ID" })).toBeTruthy();
    samplePMSchedules.forEach((pm) => {
      expect(screen.getByText(pm.id)).toBeTruthy();
    });
  });
});
