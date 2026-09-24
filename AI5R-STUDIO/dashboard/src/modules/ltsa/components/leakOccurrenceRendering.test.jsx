/**
 * LTSA_CM_UI_REMEDIATION_R1C -- occurrence/history leak rendering uses the
 * canonical tri-state (utils/leakSemantics) on every active surface:
 * UNKNOWN and partial readings are never shown as a green / confirmed
 * "No Leak", and each history row shows its own occurrence's state.
 */
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Badge } from "../../../design-system";
import { getPMCMEvidence } from "../../../api/ai5rClient";
import ConditionMonitoringOpenDesignView from "./ConditionMonitoringOpenDesignView";
import ConditionMonitoringReadingDetailPanel from "./ConditionMonitoringReadingDetailPanel";
import ConditionMonitoringReadingTable from "./ConditionMonitoringReadingTable";
import KnowledgeUnifiedHistory from "./KnowledgeUnifiedHistory";
import { assetEventStatusBadgeVariant, assetEventStatusLabel, mapConditionMonitoringReadingToEvent } from "../utils/maintenanceHistory";

vi.mock("../../../api/ai5rClient", () => ({
  getPMCMEvidence: vi.fn(),
  uploadPMCMEvidence: vi.fn(),
  pmCMEvidenceDownloadUrl: vi.fn((id) => `https://example.test/evidence/${id}`),
}));

beforeEach(() => {
  getPMCMEvidence.mockResolvedValue([]);
});

afterEach(() => {
  vi.clearAllMocks();
});

// [DE, NDE, label, tone, isSuccess]
const MATRIX = [
  [true, null, "Leak Detected — DE", "critical", false],
  [null, true, "Leak Detected — NDE", "critical", false],
  [true, true, "Leak Detected — DE & NDE", "critical", false],
  [false, false, "No Leak", "normal", true],
  [null, null, "Not Recorded", "neutral", false],
  [false, null, "No Leak — DE · NDE Not Recorded", "neutral", false],
  [null, false, "No Leak — NDE · DE Not Recorded", "neutral", false],
];

function reading(leakDe, leakNde, overrides = {}) {
  return {
    id: "CMONR-1",
    scheduleCode: "CMON-SCHED-001",
    equipmentTag: "641-P-5",
    area: "HOC",
    readingDate: "2026-08-01",
    mechsealTempDe: 84,
    mechsealTempNde: 79,
    leakDe,
    leakNde,
    pumpOperatingState: "RUNNING",
    finding: null,
    workflowStatus: "FINALIZED",
    ...overrides,
  };
}

function successColor() {
  const { unmount } = render(<Badge variant="success">ref</Badge>);
  const color = screen.getByText("ref").style.backgroundColor;
  unmount();
  return color;
}

describe("ConditionMonitoringReadingDetailPanel seal-leak badge", () => {
  it.each(MATRIX)("DE=%s NDE=%s -> %s", async (de, nde, label, _tone, isSuccess) => {
    const green = successColor();
    render(<ConditionMonitoringReadingDetailPanel reading={reading(de, nde)} />);
    const badge = (await screen.findAllByText(label)).find((el) => el.dataset.testid === "badge");
    expect(badge).toBeTruthy();
    expect(badge.style.backgroundColor === green).toBe(isSuccess);
    if (!isSuccess) {
      expect(screen.queryByText("No leak")).toBeNull(); // the pre-R1C collapse text
    }
  });
});

describe("ConditionMonitoringReadingTable leak badge", () => {
  it.each(MATRIX)("DE=%s NDE=%s -> %s", (de, nde, label, _tone, isSuccess) => {
    const green = successColor();
    render(<ConditionMonitoringReadingTable readings={[reading(de, nde)]} selectedId={null} onSelect={() => {}} />);
    const badges = screen.getAllByText(label).filter((el) => el.dataset.testid === "badge");
    expect(badges.length).toBeGreaterThan(0);
    for (const badge of badges) {
      expect(badge.style.backgroundColor === green).toBe(isSuccess);
    }
  });
});

describe("ConditionMonitoringOpenDesignView seal-leak health card", () => {
  it.each(MATRIX)("DE=%s NDE=%s -> %s", (de, nde, label, tone) => {
    render(<ConditionMonitoringOpenDesignView reading={reading(de, nde)} />);
    const card = screen.getByText("Seal Leak").closest(".workspace-health-card");
    expect(within(card).getByText(label)).toBeTruthy();
    expect(card.className).toContain(`tone-${tone}`);
  });
});

describe("maintenanceHistory CMON events", () => {
  const record = (de, nde) => ({
    condition_monitoring_reading_code: "CMONR-9",
    asset_code: "641-P-5",
    reading_date: "2026-08-01",
    mechanical_seal_leak_de: de,
    mechanical_seal_leak_nde: nde,
  });

  it.each(MATRIX)("DE=%s NDE=%s keeps raw tri-state and labels %s", (de, nde, label, _tone, isSuccess) => {
    const event = mapConditionMonitoringReadingToEvent(record(de, nde));
    expect(event.raw.leakDe).toBe(de);
    expect(event.raw.leakNde).toBe(nde);
    expect(assetEventStatusLabel(event)).toBe(label);
    expect(assetEventStatusBadgeVariant(event) === "success").toBe(isSuccess);
    expect(event.status === "NORMAL").toBe(isSuccess);
  });

  it("never turns an absent value into false", () => {
    const event = mapConditionMonitoringReadingToEvent(record(undefined, undefined));
    expect(event.raw.leakDe).toBeNull();
    expect(event.raw.leakNde).toBeNull();
    expect(event.status).toBe("LEAK_NOT_RECORDED");
    expect(event.title).not.toMatch(/normal|no leak/i);
  });

  it("keeps event identity and date", () => {
    const event = mapConditionMonitoringReadingToEvent(record(true, null));
    expect(event).toMatchObject({ id: "CMONR-9", type: "CMON", equipmentTag: "641-P-5", date: "2026-08-01", status: "LEAK_DETECTED" });
  });
});

describe("KnowledgeUnifiedHistory occurrence integrity", () => {
  it("shows each occurrence's own leak state, not the current/latest one", () => {
    const older = reading(true, null, { id: "CMONR-OLD", readingDate: "2026-07-01" });
    const newer = reading(false, false, { id: "CMONR-NEW", readingDate: "2026-08-01" });
    render(<KnowledgeUnifiedHistory conditionMonitoringReadings={[older, newer]} />);
    expect(screen.getByTestId("history-row-CMON:CMONR-OLD").textContent).toContain("Leak Detected — DE");
    expect(screen.getByTestId("history-row-CMON:CMONR-NEW").textContent).toContain("No Leak");
    expect(screen.getByTestId("history-row-CMON:CMONR-NEW").textContent).not.toContain("Leak Detected");
  });

  it.each(MATRIX)("DE=%s NDE=%s history summary -> %s", (de, nde, label) => {
    render(<KnowledgeUnifiedHistory conditionMonitoringReadings={[reading(de, nde)]} />);
    const row = screen.getByTestId("history-row-CMON:CMONR-1");
    expect(row.textContent).toContain(`RUNNING — ${label}`);
    if (de !== false || nde !== false) {
      expect(row.textContent).not.toContain("No leak recorded"); // pre-R1C collapse text
    }
  });
});
