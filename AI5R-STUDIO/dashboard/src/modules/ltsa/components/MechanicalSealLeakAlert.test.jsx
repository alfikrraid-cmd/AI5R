/**
 * LTSA_CM_UI_REMEDIATION_R1D -- the shared prominent Mechanical Seal Leak alert
 * and the surfaces it is installed on (Current Condition, Reading Detail,
 * Actual Measuring Report).
 */
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Badge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import { getPMCMEvidence } from "../../../api/ai5rClient";
import MechanicalSealLeakAlert from "./MechanicalSealLeakAlert";
import ConditionMonitoringReadingDetailPanel from "./ConditionMonitoringReadingDetailPanel";
import ConditionMonitoringReportMeasuring from "./ConditionMonitoringReportMeasuring";
import KnowledgeSummary from "./KnowledgeSummary";
import KnowledgeUnifiedHistory from "./KnowledgeUnifiedHistory";

vi.mock("../../../api/ai5rClient", () => ({
  getPMCMEvidence: vi.fn(),
  uploadPMCMEvidence: vi.fn(),
  pmCMEvidenceDownloadUrl: vi.fn((id) => `https://example.test/evidence/${id}`),
}));

beforeEach(() => getPMCMEvidence.mockResolvedValue([]));
afterEach(() => vi.clearAllMocks());

const ALERT = "mechanical-seal-leak-alert";

// [DE, NDE, state, headline | null]
const OCCURRENCES = [
  [true, null, "LEAK_DE", "LEAK DETECTED — DE"],
  [null, true, "LEAK_NDE", "LEAK DETECTED — NDE"],
  [true, true, "LEAK_DE_AND_NDE", "LEAK DETECTED — DE & NDE"],
  [false, false, "NO_LEAK", null],
  [false, null, "NO_LEAK_DE_ONLY", null],
  [null, false, "NO_LEAK_NDE_ONLY", null],
  [null, null, "UNKNOWN", null],
];

function reading(leakDe, leakNde, overrides = {}) {
  return {
    id: "CMONR-1", scheduleCode: "CMON-SCHED-001", equipmentTag: "641-P-5", area: "HOC",
    readingDate: "2026-08-01", mechsealTempDe: 84, mechsealTempNde: 79, leakDe, leakNde,
    pumpOperatingState: "RUNNING", finding: null, workflowStatus: "FINALIZED", apiPlanSnapshot: "23/61",
    ...overrides,
  };
}

function expectAlert(headline) {
  if (headline === null) {
    expect(screen.queryByTestId(ALERT)).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    return;
  }
  const alert = screen.getByTestId(ALERT);
  expect(alert.getAttribute("role")).toBe("alert");
  expect(alert.textContent).toContain(headline);
  expect(alert.textContent).toContain("Mechanical Seal Leak");
}

describe("MechanicalSealLeakAlert", () => {
  it.each(OCCURRENCES)("from raw DE=%s NDE=%s (%s)", (de, nde, _state, headline) => {
    render(<MechanicalSealLeakAlert leakDe={de} leakNde={nde} />);
    expectAlert(headline);
  });

  it.each(OCCURRENCES)("from canonical state (DE=%s NDE=%s) %s", (_de, _nde, state, headline) => {
    render(<MechanicalSealLeakAlert state={state} />);
    expectAlert(headline);
  });

  it("uses critical styling and explicit text, never colour alone", () => {
    render(<MechanicalSealLeakAlert state="LEAK_DE_AND_NDE" context="Current Condition" />);
    const alert = screen.getByTestId(ALERT);
    const dangerRef = render(<Badge variant="danger">ref</Badge>);
    expect(alert.style.backgroundColor).toBe(screen.getByText("ref").style.backgroundColor);
    dangerRef.unmount();
    expect(alert.dataset.leakState).toBe("LEAK_DE_AND_NDE");
    expect(alert.dataset.leakSide).toBe("DE_AND_NDE");
    expect(alert.textContent).toContain("Mechanical Seal Leak · Current Condition");
    expect(alert.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
  });

  it("never renders for an unrecognised or missing state", () => {
    render(<MechanicalSealLeakAlert state="WHATEVER" />);
    expect(screen.queryByTestId(ALERT)).toBeNull();
    render(<MechanicalSealLeakAlert />);
    expect(screen.queryByTestId(ALERT)).toBeNull();
  });
});

describe("Reading Detail alert (selected occurrence only)", () => {
  it.each(OCCURRENCES)("DE=%s NDE=%s (%s)", async (de, nde, state, headline) => {
    render(<ConditionMonitoringReadingDetailPanel reading={reading(de, nde)} />);
    await screen.findByText("Reading Summary");
    expectAlert(headline);
    if (state === "UNKNOWN") {
      expect(screen.getAllByText("Not Recorded").length).toBeGreaterThan(0); // R1C presentation kept
    }
  });
});

describe("Actual Measuring Report alert", () => {
  it.each(OCCURRENCES)("DE=%s NDE=%s (%s) keeps the Y / N / — table", (de, nde, _state, headline) => {
    render(<ConditionMonitoringReportMeasuring reading={reading(de, nde)} />);
    expectAlert(headline);
    const cells = screen.getByText("Mechanical Seal Leak", { selector: "th" }).closest("tr").querySelectorAll("td");
    const yn = (v) => (v === true ? "Y" : v === false ? "N" : "—");
    expect([cells[0].textContent, cells[1].textContent]).toEqual([yn(de), yn(nde)]);
    expect(screen.getByText("23/61")).toBeTruthy(); // API Plan snapshot unchanged
  });
});

describe("Current Condition alert (canonical R1B payload)", () => {
  const equipment = (currentCondition) => ({ tag: "641-P-5", name: "Pump", condition: "attention", currentCondition });
  const current = (leakState, activeLeak, extra = {}) => ({
    readingCode: "CMONR-CUR", readingDate: "2026-08-13T00:00:00", workflowStatus: "DRAFT",
    leakState, activeLeak, leakDe: null, leakNde: null, completeness: "PARTIAL", hasCurrentReading: true, ...extra,
  });

  it("LEAK_DE -> alert DE, labelled as Current Condition", () => {
    render(<KnowledgeSummary equipment={equipment(current("LEAK_DE", true, { leakDe: true }))} />);
    expectAlert("LEAK DETECTED — DE");
    expect(screen.getByTestId(ALERT).textContent).toContain("Current Condition · 2026-08-13");
  });

  it.each([["NO_LEAK"], ["NO_LEAK_DE_ONLY"], ["NO_LEAK_NDE_ONLY"], ["UNKNOWN"]])("%s -> no critical alert", (state) => {
    render(<KnowledgeSummary equipment={equipment(current(state, false))} />);
    expectAlert(null);
  });

  it("no current reading / no payload -> no alert", () => {
    render(<KnowledgeSummary equipment={equipment(null)} />);
    expectAlert(null);
    render(<KnowledgeSummary equipment={equipment(current("UNKNOWN", false, { hasCurrentReading: false, readingCode: null, readingDate: null }))} />);
    expectAlert(null);
  });

  it("uses the backend's activeLeak/state only (history is not consulted)", () => {
    // A payload claiming a leak state but not active is not shown as active.
    render(<KnowledgeSummary equipment={equipment(current("LEAK_DE", false))} />);
    expectAlert(null);
    // KnowledgeSummary has no readings/history input at all; the alert follows
    // the canonical state even if an older occurrence elsewhere leaked.
    expect(KnowledgeSummary.length).toBeLessThanOrEqual(1);
  });
});

describe("History non-regression", () => {
  it("history rows keep R1C text and never carry the prominent alert", () => {
    const older = reading(true, null, { id: "CMONR-OLD", readingDate: "2026-07-01" });
    const newer = reading(false, false, { id: "CMONR-NEW", readingDate: "2026-08-01" });
    render(<KnowledgeUnifiedHistory conditionMonitoringReadings={[older, newer]} />);
    expect(screen.queryByTestId(ALERT)).toBeNull();
    expect(screen.getByTestId("history-row-CMON:CMONR-OLD").textContent).toContain("Leak Detected — DE");
    expect(screen.getByTestId("history-row-CMON:CMONR-NEW").textContent).toContain("No Leak");
  });

  it("the older occurrence's detail and report show its own leak alert", async () => {
    const older = reading(true, null, { id: "CMONR-OLD", readingDate: "2026-07-01" });
    const detail = render(<ConditionMonitoringReadingDetailPanel reading={older} />);
    await screen.findByText("Reading Summary");
    expectAlert("LEAK DETECTED — DE");
    detail.unmount();
    render(<ConditionMonitoringReportMeasuring reading={older} />);
    expectAlert("LEAK DETECTED — DE");
  });
});

describe("Badge neutral variant", () => {
  it("is muted (border token), not purple, not success, not danger", () => {
    render(
      <>
        <Badge variant="neutral">n</Badge>
        <Badge variant="purple">p</Badge>
        <Badge variant="success">s</Badge>
        <Badge variant="danger">d</Badge>
      </>
    );
    const bg = (t) => screen.getByText(t).style.backgroundColor;
    expect(bg("n")).not.toBe(bg("p"));
    expect(bg("n")).not.toBe(bg("s"));
    expect(bg("n")).not.toBe(bg("d"));
    const ref = document.createElement("span");
    ref.style.backgroundColor = colors.border;
    expect(bg("n")).toBe(ref.style.backgroundColor);
  });

  it("unknown variants still fall back to purple (backward compatible)", () => {
    render(
      <>
        <Badge variant="nope">x</Badge>
        <Badge variant="purple">p</Badge>
      </>
    );
    expect(screen.getByText("x").style.backgroundColor).toBe(screen.getByText("p").style.backgroundColor);
  });
});

it("Current Condition alert renders once, not repeated per section", () => {
  const eq = { tag: "641-P-5", currentCondition: { leakState: "LEAK_NDE", activeLeak: true, readingDate: null } };
  const { container } = render(<KnowledgeSummary equipment={eq} />);
  expect(within(container).getAllByTestId(ALERT)).toHaveLength(1);
});
