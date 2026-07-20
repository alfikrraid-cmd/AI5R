import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CorrectiveMaintenanceReport from "./CorrectiveMaintenanceReport";
import sampleCMReports from "../data/sampleCMReports";

describe("Corrective Maintenance Report", () => {
  it("renders the report header and print button", () => {
    render(<CorrectiveMaintenanceReport />);

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("renders every sample CM report via the reused report table", () => {
    render(<CorrectiveMaintenanceReport />);

    expect(screen.getByRole("columnheader", { name: "CM ID" })).toBeTruthy();
    sampleCMReports.forEach((cm) => {
      expect(screen.getByText(cm.id)).toBeTruthy();
    });
  });
});
