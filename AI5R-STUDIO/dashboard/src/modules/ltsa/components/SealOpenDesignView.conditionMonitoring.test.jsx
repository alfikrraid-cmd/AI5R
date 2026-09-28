import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SealOpenDesignView from "./SealOpenDesignView";

// MWO-R2C3 -- component-level tests for the "Related Condition
// Monitoring" group (History tab), driven directly by props, mirroring
// SealOpenDesignView.drawingsBom.test.jsx's own convention rather than
// re-mocking the whole Seal.jsx fetch chain here.
//
// Two distinct props feed two distinct, adjacent groups on this same
// tab: `conditionMonitoringReadings` (genuine condition_monitoring_
// reading rows -> "Related Condition Monitoring") and `cmRecords`
// (legacy Corrective Maintenance cm_report rows -> the separate
// "Related CM Reports" group, untouched by this MWO, left as disclosed
// legacy domain debt). These tests prove the two never cross.

const SEAL = {
  code: "SC-101", sealId: "MS-JC-0101", name: "John Crane Type 21",
  type: "T48MP", manufacturer: "John Crane", model: null, shaftSize: 50,
  material: "Carbon/Silicon Carbide", temperatureLimit: 120, pressureLimit: 16,
  kimapPertamina: null, gpnJohnCrane: null, updatedAt: null, updatedBy: null,
  status: "ACTIVE", compatiblePumps: ["211-P-8A"], compatibleSeals: [], recommendation: null,
};

function openHistoryTab() {
  fireEvent.click(screen.getByRole("tab", { name: "History" }));
}

describe("Mechanical Seal Workspace -- Related Condition Monitoring (MWO-R2C3)", () => {
  it("renders a genuine condition_monitoring_reading row under Related Condition Monitoring", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        resolvedAssetCode="211-P-8A"
        conditionMonitoringReadings={[
          { id: "CMONR-1", assetCode: "211-P-8A", readingDate: "2026-06-01", leakDe: false, leakNde: true, tempDe: 61.5, tempNde: 58.2, status: "REVIEWED", finding: "Minor NDE weep" },
        ]}
        cmRecords={[]}
      />
    );
    openHistoryTab();

    expect(screen.getByText("CMONR-1")).toBeTruthy();
    expect(screen.getByText(/Reading 2026-06-01/)).toBeTruthy();
    expect(screen.getByText(/DE leak: No/)).toBeTruthy();
    expect(screen.getByText(/NDE leak: Yes/)).toBeTruthy();
    expect(screen.getByText("REVIEWED")).toBeTruthy();
  });

  it("never fabricates a row under Related Condition Monitoring when there are no genuine readings", () => {
    render(<SealOpenDesignView seal={SEAL} resolvedAssetCode="211-P-8A" conditionMonitoringReadings={[]} cmRecords={[]} />);
    openHistoryTab();

    const row = screen.getByText("Related Condition Monitoring").closest(".info-row");
    expect(row.textContent).toMatch(/^Related Condition Monitoring0/);
    expect(row.querySelectorAll(".part-item").length).toBe(0);
  });

  it("does not let legacy Corrective Maintenance (cmRecords) rows appear under Related Condition Monitoring", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        resolvedAssetCode="211-P-8A"
        conditionMonitoringReadings={[]}
        cmRecords={[
          { id: "CM-LEGACY-1", failureDescription: "Corrective Maintenance failure report", status: "OPEN" },
        ]}
      />
    );
    openHistoryTab();

    // The legacy row must render only under its own, separate "Related
    // CM Reports" group -- proving cmRecords is not the "cm" group's
    // data source -- and never under "Related Condition Monitoring".
    expect(screen.getByText("CM-LEGACY-1")).toBeTruthy();
    const cmGroupRow = screen.getByText("Related Condition Monitoring").closest(".info-row");
    expect(cmGroupRow.textContent).not.toMatch(/CM-LEGACY-1/);
  });

  it("does not let a genuine Condition Monitoring reading appear under the legacy Related CM Reports group", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        resolvedAssetCode="211-P-8A"
        conditionMonitoringReadings={[
          { id: "CMONR-1", assetCode: "211-P-8A", readingDate: "2026-06-01", leakDe: false, leakNde: true, tempDe: 61.5, tempNde: 58.2, status: "REVIEWED", finding: "Minor NDE weep" },
        ]}
        cmRecords={[]}
      />
    );
    openHistoryTab();

    const cmReportsRow = screen.getByText("Related CM Reports").closest(".info-row");
    expect(cmReportsRow.textContent).not.toMatch(/CMONR-1/);
  });
});
