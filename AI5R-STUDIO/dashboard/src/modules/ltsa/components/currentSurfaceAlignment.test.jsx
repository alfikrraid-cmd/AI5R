/**
 * LTSA_CM_UI_REMEDIATION_R1E -- on the Knowledge / Asset 360 screen the
 * canonical Current Condition (KnowledgeSummary, R1B payload) and a selected
 * historical occurrence (KnowledgeUnifiedHistory -> Reading Detail) are shown
 * together and must each tell their own truth.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getPMCMEvidence } from "../../../api/ai5rClient";
import KnowledgeSummary from "./KnowledgeSummary";
import KnowledgeUnifiedHistory from "./KnowledgeUnifiedHistory";
import { mapCurrentCondition } from "../utils/currentConditionMapping";

vi.mock("../../../api/ai5rClient", () => ({
  getPMCMEvidence: vi.fn(),
  uploadPMCMEvidence: vi.fn(),
  pmCMEvidenceDownloadUrl: vi.fn((id) => `https://example.test/evidence/${id}`),
}));

beforeEach(() => getPMCMEvidence.mockResolvedValue([]));
afterEach(() => vi.clearAllMocks());

const ALERT = "mechanical-seal-leak-alert";

function reading(id, readingDate, leakDe, leakNde) {
  return {
    id, scheduleCode: "UNSCHEDULED::HISTORICAL", equipmentTag: "641-P-5", area: "HOC", readingDate,
    leakDe, leakNde, pumpOperatingState: "RUNNING", finding: null, workflowStatus: "FINALIZED",
  };
}

function screenWith(currentPayload, readings) {
  const equipment = { tag: "641-P-5", name: "Pump", condition: "normal", currentCondition: mapCurrentCondition(currentPayload) };
  return render(
    <>
      <section data-testid="current-condition"><KnowledgeSummary equipment={equipment} /></section>
      <section data-testid="history"><KnowledgeUnifiedHistory conditionMonitoringReadings={readings} /></section>
    </>
  );
}

describe("Current Condition vs selected occurrence (same screen)", () => {
  it("selected 2026-02-01 leak shows its alert while canonical current (2026-07-01) is No Leak", async () => {
    // History order is deliberately misleading: the leak row is listed first.
    const older = reading("CMONR-OLD", "2026-02-01", true, null);
    const newer = reading("CMONR-CUR", "2026-07-01", false, false);
    screenWith(
      { reading_code: "CMONR-CUR", reading_date: "2026-07-01", workflow_status: "FINALIZED", state: "NO_LEAK", active: false, de: false, nde: false, completeness: "COMPLETE", has_current_reading: true },
      [older, newer]
    );

    expect(within(screen.getByTestId("current-condition")).queryByTestId(ALERT)).toBeNull();

    const oldRow = screen.getByTestId("history-row-CMON:CMONR-OLD");
    fireEvent.click(within(oldRow).getByText("View Details"));
    await within(oldRow).findByText("Reading Summary");

    const alerts = screen.getAllByTestId(ALERT);
    expect(alerts).toHaveLength(1);
    expect(oldRow.contains(alerts[0])).toBe(true);
    expect(alerts[0].textContent).toContain("LEAK DETECTED — DE");
    expect(screen.getByTestId("history-row-CMON:CMONR-CUR").textContent).toContain("No Leak");
  });

  it("canonical current leak is raised even when the newest history row shows no leak", () => {
    // The backend chose CMONR-CUR as the current reading; a newer, non-usable
    // row in the list must not override it (no frontend re-selection).
    screenWith(
      { reading_code: "CMONR-CUR", reading_date: "2026-07-01", workflow_status: "DRAFT", state: "LEAK_NDE", active: true, de: null, nde: true, completeness: "PARTIAL", has_current_reading: true },
      [reading("CMONR-NEWER", "2026-08-01", false, false), reading("CMONR-CUR", "2026-07-01", null, true)]
    );
    const alert = within(screen.getByTestId("current-condition")).getByTestId(ALERT);
    expect(alert.textContent).toContain("LEAK DETECTED — NDE");
    expect(alert.textContent).toContain("Current Condition · 2026-07-01");
  });
});

describe("Current Condition vs recent leak evidence", () => {
  it("a 90-day-old latest leak stays the current active leak (recent_leak_observed=false does not override)", () => {
    const cmSummary = {
      current_leak_condition: { reading_code: "CMONR-90D", reading_date: "2026-06-26", workflow_status: "FINALIZED", state: "LEAK_DE", active: true, de: true, nde: null, completeness: "PARTIAL", has_current_reading: true },
      recent_leak_observed: false,
    };
    screenWith(cmSummary.current_leak_condition, [reading("CMONR-90D", "2026-06-26", true, null)]);
    expect(within(screen.getByTestId("current-condition")).getByTestId(ALERT).textContent).toContain("LEAK DETECTED — DE");
  });

  it("a recent leak that is no longer current raises no current alert", () => {
    screenWith(
      { reading_code: "CMONR-CUR", reading_date: "2026-09-20", workflow_status: "FINALIZED", state: "NO_LEAK", active: false, de: false, nde: false, completeness: "COMPLETE", has_current_reading: true },
      [reading("CMONR-RECENT", "2026-09-05", true, null), reading("CMONR-CUR", "2026-09-20", false, false)]
    );
    expect(within(screen.getByTestId("current-condition")).queryByTestId(ALERT)).toBeNull();
  });

  it.each([
    ["UNKNOWN", null, null],
    ["NO_LEAK_DE_ONLY", false, null],
    ["NO_LEAK_NDE_ONLY", null, false],
  ])("canonical current %s raises no alert", (state, de, nde) => {
    screenWith(
      { reading_code: "CMONR-CUR", reading_date: "2026-09-20", workflow_status: "DRAFT", state, active: false, de, nde, completeness: "PARTIAL", has_current_reading: true },
      [reading("CMONR-CUR", "2026-09-20", de, nde)]
    );
    expect(within(screen.getByTestId("current-condition")).queryByTestId(ALERT)).toBeNull();
  });
});
